
import pandas as pd
from simpledbf import Dbf5
from scipy.stats import variation
import numpy as np
from matplotlib import pyplot as plt
import seaborn as sns
from sklearn.linear_model import LinearRegression as LR
import random
import json

def load_configurations(configuration_file):
    with open(configuration_file) as file:
        json_file = json.load(file)
        percentage = json_file['percentage']
        data_groups_explanation = json_file['data_groups_explanation']
        return percentage, data_groups_explanation


def load_data(first_path, second_path):
    dbf1 = Dbf5(first_path)
    dbf2 = Dbf5(second_path)
    df_ndvi_lst = dbf1.to_dataframe()
    df_ndvi_ndvi = dbf2.to_dataframe()
    df_ndvi_ndvi = df_ndvi_ndvi[['grid_code', 'FID_pixelc']]
    return df_ndvi_lst, df_ndvi_ndvi


def _get_data_groups(dataframe, data_groups_explaination, column):
    data_groups = {}
    for data_group in data_groups_explaination:
        if data_group['from'] == 0:
            data_groups[data_group['name']] = dataframe[dataframe[column] < data_group['to']]
            continue
        if data_group['to'] == 0:
            data_groups[data_group['name']] = dataframe[dataframe[column] >= data_group['from']]
            continue
        group = dataframe[dataframe[column] < data_group['to']]
        group = group[group[column] >= data_group['from']]
        data_groups[data_group['name']] = group
    return data_groups

def _is_valid(group):
    return len(group) > 0

def _group(dataframe, by):
    df_1k_groups = []
    for id in range(min(dataframe[by]), max(dataframe[by]) + 1):
        group = dataframe[dataframe[by] == id]
        if _is_valid(group):
            df_1k_groups.append(group)
    return df_1k_groups


def _get_coef_variation(dataframe_groups, column, id_column='FID_pixelc'):
    coefs = []
    field_id_array = []
    for group in dataframe_groups:
        coef_variation = variation(group[column])
        coefs.append(coef_variation)
        field_id_array.append(max(group[id_column]))
    return pd.DataFrame({id_column: field_id_array, 'coef_variation': coefs})

def _get_chosen_dataframe_including_ids(dataframe, ids, column='FID_pixelc'):
    drop_ids = []
    chosen_dataframe = pd.DataFrame()
    empty_rows = 0
    for i in ids:
        row = dataframe[dataframe[column] == i]
        if len(row) == 0:
            empty_rows += 1
            drop_ids.append(i)
        chosen_dataframe = chosen_dataframe.append(row)
    return chosen_dataframe, empty_rows, drop_ids


def _drop_unmatched_rows(df, drop_ids):
    for id in drop_ids:
        df['FID_pixelc'].replace(id, np.nan, inplace=True)
    df.dropna(inplace=True)
    df.reset_index(inplace=True)
    

def get_ndvi_lst_variation_df():

    first_path = input("please input the ndvi lst file path: ")
    second_path = input("please input the ndvi ndvi file path: ")

    print('starting the processing....')


    # load bot data for ndvi ndvi and for ndvi lst
    df_ndvi_lst, df_ndvi_ndvi = load_data(first_path, second_path)
    
    print('grouping the data by their ndvi pixel id...')
    # group ndvi 30m by their 1km squared parent pixel 
    df_ndvi_ndvi_groups = _group(df_ndvi_ndvi, 'FID_pixelc')
    
    print('calculating the coef of variation...')
    # calculate the coef of vaiation for the groups
    df = _get_coef_variation(df_ndvi_ndvi_groups, 'grid_code')
    
    # get the chosen data from the dataframe using the ids
    df_ndvi_lst_clipped, empty, drop_ids = _get_chosen_dataframe_including_ids(df_ndvi_lst, df['FID_pixelc'])
    
    # reset the index so we can compare them to each other
    df.reset_index(inplace=True)
    
    # sort the tables to make sure that they are in the same order
    
    df_ndvi_lst_clipped.sort_values(by=['FID_pixelc'], inplace=True)
    df.sort_values(by=['FID_pixelc'], inplace=True)
    df_ndvi_lst_clipped.reset_index(inplace=True)

    _drop_unmatched_rows(df, drop_ids)

    df_ndvi_lst_clipped['coef_variation'] = df['coef_variation']
    
    return df_ndvi_lst_clipped
    

def _compute_first_percentage_of_groups(df_groups, percentage=0.25):
    group_populations = {name: len(df_groups[name]['grid_code']) for name in df_groups}
    for group in df_groups:
        df_groups[group].sort_values(by=['coef_variation'], inplace=True)
        first_25_percent = int(group_populations[group] * percentage)
        df_groups[group] = df_groups[group][:first_25_percent]

def get_cleaned_data(data_groups_explanation, df_ndvi_lst_variation, percentage=0.25):
    df_groups = _get_data_groups(df_ndvi_lst_variation, data_groups_explanation, 'grid_code')
    _compute_first_percentage_of_groups(df_groups, percentage)
    cleaned_data = pd.DataFrame()
    for group in df_groups:
        cleaned_data = cleaned_data.append(df_groups[group])
    return cleaned_data


def main():
    ndvi_lst_variation_df = get_ndvi_lst_variation_df()

    print('loading configurations...')
    percentage, data_Group_explanation = load_configurations('configuration.json')

    print('generating cleaned data....')
    df_cleaned_data = get_cleaned_data(data_Group_explanation, ndvi_lst_variation_df, percentage)

    print('exporting cleaned data to an excel sheet...')
    file_name = f'cleaned_data_{random.randint(0, 10000000)}.xlsx'
    df_cleaned_data.to_excel(file_name) 
    print('done successfully.')
    
    plt.scatter(df_cleaned_data['grid_code'], df_cleaned_data['grid_code_'])
    plt.savefig('filename.svg')

if __name__ == '__main__':
    main()
