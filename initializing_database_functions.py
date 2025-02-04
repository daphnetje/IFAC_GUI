from detect_discriminatory_patterns import find_disc_patterns
import pandas as pd

def load_in_adult_dataset():
    dataset = pd.read_csv('adult_sample.csv')

    db = get_db()

    for index, row in dataset.iterrows():
        db.execute('insert into adult_dataset (age, marital_status, hours_per_week, education,work_sector, occupation ,race,sex,income, age_num, hours_per_week_num, education_num) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', \
                   [row['age'], row['marital_status'], row['hours.per.week'],
                    row['education'], row['work_sector'], row['occupation'],
                    row['race'], row['sex'], row['income'], row['age.num'],
                    row['hours.per.week.num'], row['education.num']])
        db.commit()
    dataset_loaded = True


def load_in_decision_rules():
    dataset = pd.read_csv('adult_sample.csv')
    dataset = dataset[['age', 'marital_status', 'hours.per.week', 'education', 'work_sector', 'occupation', 'race', 'sex', 'income']]

    find_disc_patterns(dataset)


