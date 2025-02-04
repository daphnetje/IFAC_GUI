from flask import Flask, request, jsonify, url_for, redirect, session, render_template, g
from flask_caching import Cache
import sqlite3
from database_helper_functions import query_builder_multiple_filters, get_indices_covered_by_pattern
from pretty_html_functions import rule_dict_to_html, one_instance_html, protected_info_html, decision_ratio_information
from situation_testing import number_of_positive_decisions, run_situation_testing
from initializing_database_functions import load_in_decision_rules

import pandas as pd

app = Flask(__name__)
cache = Cache(app, config={'CACHE_TYPE': 'simple'})
app.config['DEBUG'] = True
app.config['SECRET_KEY'] = 'Tf42Cq7ZtH5TsoZfiYXrpSkN7xUGzWaV'

dataset_dict = {'age': ["Younger than 30", "30 - 39", "40-49", "50-59", "Older than 60"],
                'marital_status': ['Never married', 'Married', 'Seperated', 'Widowed'],
                'hours_per_week' : ["Less than 20", "20 to 39", "40 to 49", "More than 50"],
                'education' : ['Middle School', 'High School', 'Higher Ed.', 'Bachelors', 'Masters', 'Doctorate'],
                'work_sector' : ['self-employed', 'private', 'government'],
                'occupation': ['Exec-managerial', 'Machine-op-inspct', 'Prof-specialty', 'Other-service', 'Adm-clerical', 'Transport-moving', 'Sales', 'Craft-repair', 'Farming-fishing', 'Tech-support', 'Other', 'Handlers-cleaners'],
                'race' : ['White', 'Black'],
                'sex' : ["Female", "Male"],
                'income' : ['<=50K', '>50K'],
                'age_num': [1, 2, 3, 4, 5],
                'hours_per_week_num': [1, 2, 3, 4],
                'education_num': [1, 2, 3, 4, 5, 6, 7]}
numerical_columns = ['age_num', 'hours_per_week_num', 'education_num']
all_columns = ['id', 'age', 'marital_status', 'hours_per_week', 'education', 'work_sector', 'occupation', 'race', 'sex', 'income', 'age_num', 'hours_per_week_num', 'education_num']

dataset_loaded = False

def connect_db():
    sql = sqlite3.connect('bias_detection.db')
    #ensures that rows are displayed as python dictionaries instead of tuples
    sql.row_factory = sqlite3.Row
    return sql

def get_db():
    if not hasattr(g, 'sqlite3'):
        g.sqlite_db = connect_db()
    return g.sqlite_db


@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()


@app.route('/', methods = ['GET', 'POST'])
def index():
    if request.method == 'POST':
        selected_column_filters = {}

        # Get the number of dynamically generated select fields
        num_select_fields = len([key for key in request.form.keys() if key.startswith('dependent_select_')])

        # Iterate through the select fields and insert data into the database
        for i in range(1, num_select_fields + 1):
            selected_column_name = request.form.get(f'main_select_{i}')
            selected_value = request.form.get(f'dependent_select_{i}')
            selected_column_filters[selected_column_name] = selected_value

        db = get_db()
        query_to_filter, values_to_filter = query_builder_multiple_filters(selected_column_filters)
        adult_dataset_cursor = db.execute(query_to_filter, values_to_filter)
        results = adult_dataset_cursor.fetchall()
        print(len(results))
        adult_dataset_cursor.close()
        return render_template('home.html', column_names=dataset_dict.keys(), numerical_cols = numerical_columns, results=results, number_of_results = len(results))

    db = get_db()
    adult_dataset_cursor = db.execute('select * from adult_dataset')
    results = adult_dataset_cursor.fetchall()
    adult_dataset_cursor.close()
    return render_template('home.html', column_names = dataset_dict.keys(),numerical_cols = numerical_columns, results = results, number_of_results = len(results))


@app.route('/inspect_patterns', defaults = {'pattern_id': -99999}, methods = ['GET'])
@app.route('/inspect_patterns/<pattern_id>', methods = ['GET', 'POST'])
def inspect_patterns(pattern_id):
    db = get_db()

    #get all discriminatory patterns
    disc_patterns_cursor = db.execute('select * from discriminatory_patterns')
    disc_patterns_results = disc_patterns_cursor.fetchall()
    disc_decision_rules = [rule_dict_to_html(result) for result in disc_patterns_results]

    #get all the dataset instances to show in table
    adult_dataset_cursor = db.execute('select age, marital_status, hours_per_week, education, work_sector, occupation, race, sex, income, age_num, hours_per_week_num, education_num from adult_dataset')
    dataset_results = adult_dataset_cursor.fetchall()
    adult_dataset_cursor.close()

    relevant_indices = []
    number_of_affected_instances = 0
    #depending on whether a pattern has been selected get the dataset instances (indicated by their indices) that fall
    #under this pattern and that need to be highlighted

    disc_scores_list = []
    indices_to_highlight = []
    if (pattern_id != -99999):
        selected_pattern_cursor = db.execute('select * from discriminatory_patterns where id = ?', [pattern_id])
        selected_pattern = selected_pattern_cursor.fetchone()

        #put the dataset (that already has been fetched in previous query) in df format
        dataset = pd.DataFrame.from_records(data=dataset_results, columns=dataset_dict.keys())

        relevant_indices = get_indices_covered_by_pattern(selected_pattern, dataset)
        number_of_affected_instances = len(relevant_indices)

        disc_scores_of_relevant_indices, distances_to_protected_df, distances_to_reference_group_df = run_situation_testing(selected_pattern, {'sex':'Female'}, relevant_indices, dataset)
        disc_scores_list = disc_scores_of_relevant_indices.tolist()


    if request.method == 'POST':
        selected_index = int(request.form['selected_index'])
        disc_score_of_index = disc_scores_of_relevant_indices.loc[selected_index]

        distances_of_index_to_protected = distances_to_protected_df.loc[selected_index]
        distances_of_index_to_ref_group = distances_to_reference_group_df.loc[selected_index]
        closest_prot_indices = distances_of_index_to_protected[distances_of_index_to_protected <= 0.5].index.tolist()
        closest_prot_indices_string_format = ','.join(str(i) for i in closest_prot_indices)

        closest_ref_group_indices = distances_of_index_to_ref_group[distances_of_index_to_ref_group <= 0.5].index.tolist()
        closest_ref_group_indices_string_format = ','.join(str(i) for i in closest_ref_group_indices)

        if closest_ref_group_indices_string_format == "":
            closest_ref_group_indices_string_format = "None"
        return redirect(url_for("inspect_nearest_neighbours", index = selected_index, disc_score = disc_score_of_index, closest_prot=closest_prot_indices_string_format, closest_ref=closest_ref_group_indices_string_format))

    return render_template('inspect_discriminatory_patterns.html', column_names = dataset_dict.keys(),
                           numerical_cols = numerical_columns, dataset_results = dataset_results,
                           rules = disc_decision_rules, active_pattern_id = int(pattern_id),
                           indices_to_highlight = relevant_indices, disc_scores_of_indices = disc_scores_list,
                           number_of_affected_instances = number_of_affected_instances)


@app.route('/inspect_nearest_neighbours/<index>/<disc_score>/<closest_prot>/<closest_ref>', methods=['GET', 'POST'])
def inspect_nearest_neighbours(index, disc_score, closest_prot, closest_ref):
    db = get_db()

    id_in_database = str(int(index) + 1)
    selected_instance_cursor = db.execute("SELECT age, marital_status, hours_per_week, education, work_sector, occupation, race, sex, income from adult_dataset WHERE id=?",[id_in_database])
    selected_instance = selected_instance_cursor.fetchone()
    selected_instance_html = one_instance_html(selected_instance, columns=dataset_dict.keys(),
                                               numerical_columns=numerical_columns, sensitive_columns=['race', 'sex'])
    prot_info_html = protected_info_html(selected_instance)

    if (closest_prot != 'None'):
        closest_prot_list = list(closest_prot.split(","))
        #+1 is not so nice here, it's because database ids start counting from 1 rather than 0. should change this in database!!
        closest_prot_list = [int(i)+1 for i in closest_prot_list]
        closest_prot_placeholder = ','.join(['?'] * len(closest_prot_list))

        adult_dataset_cursor_prot = db.execute(f"SELECT * FROM adult_dataset WHERE id IN ({closest_prot_placeholder})", closest_prot_list)
        dataset_closest_prot_results = adult_dataset_cursor_prot.fetchall()
        dataset_closest_prot_results_df = pd.DataFrame.from_records(data=dataset_closest_prot_results, columns=all_columns)
        pos_decision_ratio_prot = number_of_positive_decisions(dataset_closest_prot_results_df['income'])/len(dataset_closest_prot_results)
        pos_decision_ratio_prot_html = decision_ratio_information(len(dataset_closest_prot_results_df), pos_decision_ratio_prot)
    else:
        pos_decision_ratio_prot_html = ""
        dataset_closest_prot_results = "None"

    if (closest_ref!= 'None'):
        closest_ref_list = list(closest_ref.split(","))
        closest_ref_list = [int(i) + 1 for i in closest_ref_list]
        closest_ref_placeholder = ','.join(['?'] * len(closest_ref_list))

        adult_dataset_cursor_ref = db.execute(f"SELECT * FROM adult_dataset WHERE id IN ({closest_ref_placeholder})",
                                               closest_ref_list)
        dataset_closest_ref_results = adult_dataset_cursor_ref.fetchall()
        dataset_closest_ref_results_df = pd.DataFrame.from_records(data=dataset_closest_ref_results,
                                                                    columns=all_columns)
        pos_decision_ratio_ref = number_of_positive_decisions(dataset_closest_ref_results_df['income']) / len(
            dataset_closest_ref_results)
        pos_decision_ratio_ref_html = decision_ratio_information(len(dataset_closest_ref_results_df),
                                                                  pos_decision_ratio_ref)
    else:
        pos_decision_ratio_ref_html = ""
        dataset_closest_ref_results = "None"

    return render_template('inspect_nearest_neighbours.html', selected_index=index, prot_info = prot_info_html, selected_instance_html = selected_instance_html,
                           selected_instance=selected_instance, disc_score = disc_score, closest_prot_results = dataset_closest_prot_results,
                           closest_ref_results = dataset_closest_ref_results, pos_ratio_prot = pos_decision_ratio_prot_html, pos_ratio_ref = pos_decision_ratio_ref_html,
                           column_names = dataset_dict.keys(), numerical_cols = numerical_columns)

if __name__=='__main__':
    app.run(debug = True)

