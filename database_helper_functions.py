import pandas as pd
import json


def query_builder_multiple_filters(column_value_filter_dict):
    value_list = []

    query = 'select * from adult_dataset where'
    i = 0
    for column_filter in column_value_filter_dict:
        if i > 0:
            query += ' AND'
        query += " " + column_filter + " = (?)"
        i += 1
        value_list.append(column_value_filter_dict[column_filter])

    return query, value_list


def get_instances_covered_by_rule_base_and_consequence(rule_base, rule_consequence, data):
    relevant_data = data
    for key in rule_base.keys():
        relevant_data = relevant_data[relevant_data[key] == rule_base[key]]

    for key in rule_consequence.keys():
        relevant_data = relevant_data[relevant_data[key] == rule_consequence[key]]

    return relevant_data


def get_instances_covered_by_rule_base(rule_base, data):
    relevant_data = data
    for key in rule_base.keys():
        relevant_data = relevant_data[relevant_data[key] == rule_base[key]]

    return relevant_data


def get_indices_covered_by_pattern(pattern, dataset_df):
    rule_base_dict = json.loads(pattern['rule_base'])
    rule_consequence_dict = json.loads(pattern['rule_conclusion'])

    instances_covered = get_instances_covered_by_rule_base_and_consequence(rule_base_dict, rule_consequence_dict, dataset_df)

    indices_of_instances_covered = list(instances_covered.index.values)
    return indices_of_instances_covered