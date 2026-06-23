### this loads the WTO data
## adds dynamic income
## saves a new file

import pandas as pd
import os
import openpyxl

print(os.getcwd()) ## check working directory

datapath = "../data/"

data = pd.read_excel('../data/wtoCTDSpeakerParagraphMto117.xlsx', engine='openpyxl')

print(data.shape)
print(data.columns)
#print(data.head(5))
data = data.drop('Unnamed: 0', axis=1)

data = data.rename(columns={'income_level_iso3c': 'inc_level_abbrev'})

## Clean up some empty cells:
## cleaning up non values:
#data2.to_clipboard() #3 ugly hack to copy to excel to hunt for those nans

# Replace empty strings and whitespace-only strings with NaN
data.replace(r'^\s*$', pd.NA, regex=True, inplace=True)

## fill empty cells:
data.loc[data['codes'].isna() & data['country'].isna(), 'codes'] = 'metadata'
data.loc[data['codes'].isna() & data['country'].isna(), 'country'] = 'metadata'
data.loc[data['codes'].isna() & data['country'].isna(), 'inc_level_abbrev'] = 'metadata'
data.loc[data['codes'].isna() & data['country'].isna(), 'pres.speaker'] = 'metadata'
data.loc[(data['codes'] == 'EUN') & (data['country'].isna()), 'country'] = 'The_european_union'

## insert time-varying income levels:
inc_evol = pd.read_excel('../data/CLASS_hist.xlsx', engine='openpyxl')
inc_evol = inc_evol.drop(['fcv','lending' ,'Notes'], axis=1)
print(inc_evol.head(5))

## adjust some names:

## adjust the names to my set:
inc_evol.loc[inc_evol.country== 'TUR', 'country_name'] = 'Turkey'
inc_evol.loc[inc_evol.country== 'CIV', 'country_name'] = "Cote d'Ivoire"
inc_evol.loc[inc_evol.country== 'CZE', 'country_name'] = 'Czech Republic'

## double check any gaps:

non_overlap = set(data['country']).difference(inc_evol['country_name'])
print(non_overlap) #nan, NONST
non_overlap_codes = set(data['codes']).difference(inc_evol['country'])
print(non_overlap_codes)

inc_evol = inc_evol.rename(columns={'country': 'country_code'})

## Merge in the time-varying income level
data2 = pd.merge(data, inc_evol[['country_code', 'year', 'income']], 
                 how = 'left', 
                 left_on=['codes', 'year'], 
                 right_on= ['country_code', 'year'])

## some basic cleanup:
data2 = data2.rename(columns={'income': 'dynamic_income'})

## fill corner cases:

## Corner cases:
data2.loc[data2.codes == 'EUN', 'dynamic_income'] = 'Aggregated'
data2.loc[data2.codes == 'NONST', 'dynamic_income'] = 'Nonstate'
data2.loc[data2.codes == 'metadata', 'dynamic_income'] = 'Nonstate'
data2.loc[data2['codes'].isna() & data['country'].isna(), 'dynamic_income'] = 'metadata'

##
print(data2.shape) ## 11737
data2 = data2.drop('country_code', axis = 1) #(11737, 26)

## Map abbreviations:

income_map = {
    'Nonstate': 'NONST',
    'High income': 'HIC',
    'Upper middle income': 'UMC',
    'Lower middle income': 'LMC',
    'Low income': 'LIC',
    'Aggregated': 'AGG' 
}

data2['inc_level_abbrev'] = data2['dynamic_income'].map(income_map)

## save

#data2.to_csv("wto_M1_to_117.")