import json
from markupsafe import Markup


def rule_dict_to_html(rule, max_rule_length=3):
    rule_base_dict = json.loads(rule['rule_base'])
    rule_consequence_dict = json.loads(rule['rule_conclusion'])

    pretty_html = ''
    for key, value in rule_base_dict.items():
        pretty_html += key + " = " + value + "<br>"

    line_breaks_to_add = max_rule_length-len(rule_base_dict) + 1
    for i in range(line_breaks_to_add):
        pretty_html += '<br>'

    rule_consequence_key = list(rule_consequence_dict.keys())[0]
    pretty_html += rule_consequence_key + " = " + rule_consequence_dict[rule_consequence_key]

    complete_rule = {'id': int(rule['id']), 'rule_in_html': Markup(pretty_html), 'rule_base': rule_base_dict,
                     'rule_conclusion': rule_consequence_dict, 'support': rule['support'], 'confidence': rule['confidence'], \
                     'slift': rule['slift']}

    return complete_rule


def one_instance_html(instance, columns, numerical_columns, sensitive_columns):
    pretty_html = ''
    for column in columns:
        if (column not in numerical_columns) & (column not in sensitive_columns):
            pretty_html += "<b>" + column + "</b> = <i>" + instance[column] + "</i> <br>"
    return Markup(pretty_html)


def protected_info_html(instance):
    pretty_html = instance['race'].capitalize()
    if instance['sex'] == 'Female':
        pretty_html += " Woman"
    else:
        pretty_html += " Man"
    return pretty_html


def decision_ratio_information(number_of_instances, pos_decision_ratio):
    percentage_ratio = pos_decision_ratio * 100
    return f"We found {number_of_instances} similar instances of which {percentage_ratio:.2f}% have a high income"
