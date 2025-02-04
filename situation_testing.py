import pandas as pd
from scipy.spatial.distance import cdist
import json
from database_helper_functions import get_instances_covered_by_rule_base_and_consequence, get_instances_covered_by_rule_base



def number_of_positive_decisions(decision_vector):
    value_counts = decision_vector.value_counts()
    if '>50K' in value_counts.keys():
        return value_counts['>50K']
    else:
        return 0

def run_situation_testing(selected_pattern, prot_group_of_pattern, relevant_indices, dataset):
    #get the instances that are covered by some rule and only keep the numerical columns (needed to compute distance
    #function for situation testing)
    relevant_instances = dataset.iloc[relevant_indices]
    relevant_instances_numerical_format = relevant_instances[['age_num', 'marital_status', 'hours_per_week_num',
                                                              'education_num', 'work_sector', 'occupation', 'race',
                                                              'sex', 'income']]

    #similar instances are found within the space of other instances that are covered by rule base (excluding the prot.
    #information from rule base)
    rule_base_dict = json.loads(selected_pattern['rule_base'])
    rule_base_without_protected_group = {k: v for k, v in rule_base_dict.items() if k not in prot_group_of_pattern}
    #TODO: consider if I really want to only search among instances for which the rule base is covered
    dataset = get_instances_covered_by_rule_base(rule_base_without_protected_group, dataset)
    dataset_numerical_format = dataset[['age_num', 'marital_status', 'hours_per_week_num',
                                                              'education_num', 'work_sector', 'occupation', 'race',
                                                              'sex', 'income']]

    #extract group of other protected instances and reference group
    reference_group = dataset_numerical_format[(dataset['sex'] == 'Male') & (dataset['race'] == 'White')]
    #STILL HAVE TO DECIDE HERE WHAT WE WILL TAKE AS OTHER PROT INSTANCES (maybe best to look within specific intersectional
    # spaces like, white women, black women, black men, etc)
    other_protected_instances = dataset_numerical_format[(dataset['sex'] != 'Male') | (dataset['race'] != 'White')]

    distances_to_protected = cdist(relevant_instances_numerical_format, other_protected_instances,
                                   metric=distance_function_adult_dataset)
    distances_to_protected_df = pd.DataFrame(distances_to_protected, columns=other_protected_instances.index,
                                             index=relevant_instances_numerical_format.index)

    distances_to_reference_group = cdist(relevant_instances_numerical_format, reference_group,
                                   metric=distance_function_adult_dataset)
    distances_to_reference_group_df = pd.DataFrame(distances_to_reference_group, columns=reference_group.index,
                                             index=relevant_instances_numerical_format.index)

    disc_scores = []
    i = 0
    #for index in range(len(relevant_instances_numerical_format)):
    for index in relevant_indices:
        distance_row_protected = distances_to_protected_df.loc[index]
        closest_indices_protected = distance_row_protected[distance_row_protected <= 0.5].index.tolist()
        # sorted = distance_row_protected.argsort()
        # sorted_indices_protected = distance_row_protected.iloc[sorted].index
        # closest_indices_protected = sorted_indices_protected[:5]
        decision_info_closest_prot_neighbours = other_protected_instances.loc[closest_indices_protected]['income']

        distance_row_unprotected = distances_to_reference_group_df.loc[index]
        closest_indices_unprotected = distance_row_unprotected[distance_row_unprotected <= 0.5].index.tolist()
        # sorted = distance_row_unprotected.argsort()
        # sorted_indices_unprotected = distance_row_unprotected.iloc[sorted].index
        # closest_indices_unprotected = sorted_indices_unprotected[:5]
        decision_info_closest_unprot_neighbours = reference_group.loc[closest_indices_unprotected]['income']


        number_of_similar_prots = len(decision_info_closest_prot_neighbours)
        number_of_similar_refs = len(decision_info_closest_unprot_neighbours)

        if number_of_similar_prots > 0:
            ratio_pos_labels_prot = number_of_positive_decisions(decision_info_closest_prot_neighbours) / len(decision_info_closest_prot_neighbours)

        if number_of_similar_refs > 0:
            ratio_pos_labels_unprot = number_of_positive_decisions(decision_info_closest_unprot_neighbours)  / len(decision_info_closest_unprot_neighbours)

        if (number_of_similar_refs == 0) | (number_of_similar_prots == 0) :
            disc_score = -999
        else:
            disc_score = ratio_pos_labels_unprot - ratio_pos_labels_prot

        disc_scores.append(disc_score)

    disc_scores = pd.Series(disc_scores, index=relevant_indices)
    return disc_scores, distances_to_protected_df, distances_to_reference_group_df


def distance_function_adult_dataset(x1, x2):
    age_diff = abs(x1[0] - x2[0]) / 4

    if x1[1] == x2[1]:
        marital_status_diff = 0
    else:
        marital_status_diff = 0.5

    hours_per_week_diff = abs(x1[2] - x2[2]) / 3
    education_diff = abs(x1[3] - x2[3]) / 6

    if x1[4] == x2[4]:
        work_sec_diff = 0
    else:
        work_sec_diff = 0.5

    if x1[5] == x2[5]:
        occupation_diff = 0
    else:
        occupation_diff = 0.5

    return age_diff + marital_status_diff + hours_per_week_diff + education_diff + work_sec_diff + occupation_diff
#
# def run_situation_testing(selected_pattern, prot_group_of_pattern, relevant_indices, dataset, cache):
#     distance_matrix = cache.get("distance_matrix")
#     if (distance_matrix is not None):
#         print("we've found the matrix")
#
#     if (distance_matrix is None):
#         print("In if")
#         initializing_parameters_for_cache(dataset, cache)
#         distance_matrix = cache.get("distance_matrix")
#
#     relevant_distance_rows = distance_matrix.iloc[relevant_indices]
#
#     protected_instances = cache.get("protected_instances")
#     unprotected_instances = cache.get("unprotected_instances")
#
#     distances_to_protected_indices = distance_matrix[protected_instances.index]
#     distances_to_unprotected_indices = distance_matrix[unprotected_instances.index]
#
#     disc_scores = []
#     i = 0
#     for index in range(len(relevant_distance_rows)):
#
#         distance_row_protected = distances_to_protected_indices.iloc[index]
#         sorted = distance_row_protected.argsort()
#         sorted_indices_protected = distance_row_protected.iloc[sorted].index
#         closest_indices_protected = sorted_indices_protected[:5]
#         decision_info_closest_prot_neighbours = protected_instances.loc[closest_indices_protected]['income']
#
#         distance_row_unprotected = distances_to_unprotected_indices.iloc[index]
#         sorted = distance_row_unprotected.argsort()
#         sorted_indices_unprotected = distance_row_unprotected.iloc[sorted].index
#         closest_indices_unprotected = sorted_indices_unprotected[:5]
#         decision_info_closest_unprot_neighbours = unprotected_instances.loc[closest_indices_unprotected]['income']
#
#         ratio_pos_labels_prot = number_of_positive_decisions(decision_info_closest_prot_neighbours) / 5
#         ratio_pos_labels_unprot = number_of_positive_decisions(decision_info_closest_unprot_neighbours) / 5
#
#         disc_score = ratio_pos_labels_unprot - ratio_pos_labels_prot
#         disc_scores.append(disc_score)
#
#     return disc_scores, distances_to_protected_indices, distances_to_unprotected_indices
