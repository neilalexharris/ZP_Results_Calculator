import pandas as pd
import os

from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

folderpath = os.path.abspath('')

# initiate Chrome driver
opts = Options()
opts.add_argument('--headless')
driver = Chrome(options = opts)

def main():

    race_ids = get_race_ids() #935293 #935289 #get_race_id()

    # import BCSE teams
    filepath = r"%s/bcse_teams.csv" % folderpath
    teams = pd.read_csv(filepath)

    # import points
    filepath = r"%s/points.csv" % folderpath
    pts = pd.read_csv(filepath)

    # initialize empty dataframes
    total = pd.DataFrame()
    no_tag = pd.DataFrame()
    no_team = pd.DataFrame()

    for race_id in race_ids:

        # import race data
        print("Importing data from ZP for race: %s....." % race_id)
        df = import_race_data(driver, race_id)

        # *** CLEAN UP DATA ***
        print("Cleaning %s data....." % race_id)
        # drop unnecessary columns
        df = df.drop(['#','Gain'], axis=1)

        # rename columns
        df = df.rename(columns={'Unnamed: 0': 'Cat', 'Avg':'HR_Avg', 'Max':'HR_Max'})

        # add race number
        df['race_id'] = race_id

        # clean up name column
        df['Rider'] = df['Rider'].str.strip()

        # filter out non-bcse
        data = df.loc[df['Rider'].str.endswith(tuple(teams['team_tag']))].copy()
        nb = df.loc[~df['Rider'].str.endswith(tuple(teams['team_tag']))].copy()

        # now extract team name
        searchstr = '|'.join(teams['team_tag'])
        data['Team'] = data['Rider'].str.extract("(" + searchstr + ")", expand=False)

        # get rider names
        rider = data['Rider'].str.split(expand=True)

        data['forename'] = rider[0]
        data['surname'] = rider[1]

        # split into categories
        a = data.loc[data['Cat']=='A'].copy().reset_index()
        b = data.loc[data['Cat']=='B'].copy().reset_index()
        c = data.loc[data['Cat']=='C'].copy().reset_index()
        d = data.loc[data['Cat']=='D'].copy().reset_index()
        e = data.loc[data['Cat']=='E'].copy().reset_index()

        # allocate points per each category
        cats = ['A','B','C','D','E']

        print("Calculating BCSE points for race %s..." % race_id)
        # split into categories
        dfs = [a,b,c,d,e]
        for i, df in enumerate(dfs):

            if len(df.index) > 0:

                df['position'] = df.index+1

                col = cats[i]

                dfs[i] = pd.merge(df, pts[[col]], left_index=True, right_index=True)

                # rename points column
                dfs[i].rename(columns={col: 'Points'}, inplace=True)

                # fill backmarkers with 1 point
                dfs[i]['Points'].fillna(1, inplace=True)

                # drop unnecessary index column
                dfs[i].drop('index', axis=1, inplace=True)

        [a,b,c,d,e] = dfs

        # # add new 'B' cat scoring in
        # if len(b) > 55:
        #     # placeholder

        #     # increment => 50/len(b)

        #     # b.loc[6:,'points']

        # check for any missed BCSEs
        ntm = nb.loc[nb['Rider'].str.contains('BCSE')]
        no_team = pd.concat([no_team, ntm])

        # show BCSEs without tag in name
        ntg = data.loc[~data['Rider'].str.contains('BCSE')]
        no_tag = pd.concat([no_tag, ntg])

        # create main dataset again
        data = pd.concat([a,b,c,d,e])

        # race data to total
        total = pd.concat([total, data])

        print("")


    # **** CREATE OUTPUT ****
    print("Outputting results.....")
    create_output(total)


# **** FUNCTIONS ****

def get_race_ids():

    response = input("Please enter race ids (separated by commas):\n")

    race_ids = response.split(',')

    race_ids = [int(x) for x in race_ids]

    return race_ids

def html_to_df(driver):

    # convert results table into dataframe
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    table = soup.find(id='table_event_results_final')
    df = pd.read_html(str(table))[0]

    return df

def import_race_data(driver, race_id):

    # set url
    url = 'https://zwiftpower.com/events.php?zid=%d' % race_id

    # open page
    driver.get(url)

    data = True
    results = pd.DataFrame()
    while data == True:

        df = html_to_df(driver)

        # add results to exisiting data
        results = pd.concat([results, df])

        # check if there are other pages of results
        nxt = driver.find_elements_by_class_name('paginate_button.next.disabled')

        data = False
        # click on 'Next' button if enabled
        if len(nxt) == 0:
            btn = driver.find_element_by_class_name('paginate_button.next')
            lnk = btn.find_element_by_link_text('Next')
            lnk.click()
            data = True

    return results

def create_output(df):

    # output individual results
    df.to_csv(r'%s/individual_results.csv' % folderpath)

    # calculate team points by category
    team_by_cat = df.groupby(['race_id','Cat','Team'])['Points'].sum().reset_index()
    team_by_cat = team_by_cat.sort_values(by=['race_id','Cat','Points'], ascending=[True, True, False])
    team_by_cat.to_csv(r'%s/team_results_by_cat.csv' % folderpath)

    # calculate total points
    total_team = df.groupby(['Team'])['Points'].sum().sort_values(ascending=False)
    total_team.to_csv(r'%s/team_total.csv' % folderpath)


if __name__ == '__main__':
    main()
