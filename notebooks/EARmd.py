"""
Written by Sean Gordon and contributed to by Aleksandar Jelenak.
Using the NOAA rubrics Dr Habermann created, and his work
conceptualizing the documentation language so that rubrics using
recommendations from other earth science communities can be applied
to multiple metadata dialects as a part of the USGeo BEDI and
NSF DIBBs projects. This python module as an outcome of DIBBs allows
a user to initiate an evaluation of valid XML and assess the degree
to which the collection of records is likely to meet a community information need.

The basic workflow is to retrieve records, evaluate for xpaths that contain
text, run occurrence functions on csv output of evaluation, create reports with 
the outputs, if you want to compare between collections, combine csv outputs with
appropriate combination functions, create organizationSpreadsheet. Finally run 
WriteToGoogle on any outputs you want to share to get a viewable/downloadable link.
"""


import pandas as pd
import csv
import gzip
import os
import requests
import xlsxwriter
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from lxml import etree
import sys
import logging
from IPython.core.display import display, HTML

import itertools
from plotly import tools
import plotly.plotly
import plotly.graph_objs as go
from _plotly_future_ import v4

import plotly.io as pio
from plotly.offline import iplot, init_notebook_mode

pio.orca.config.use_xvfb = True
init_notebook_mode(connected=True)
from PIL import Image
Image.MAX_IMAGE_PIXELS = None

lggr = logging.getLogger(__name__)
csv.field_size_limit(sys.maxsize)


# function to download metadata


def get_records(urls, xml_files, well_formed=True):
    """Download metadata records. Metadata records are download from the
    supplied ``urls`` and stored in files whose names are found on
    ``xml_files``. When ``well_formed`` is ``True`` downloaded XML will
    be saved to a file only if well-formed.
    """
    """ if we used a function
    like this to collect xml, it would be the root of any processing steps
    """
    if len(urls) != len(xml_files):
        raise ValueError('Different number of URLs and record file names')

    for url, fname in zip(urls, xml_files):
        try:
            r = requests.get(url)
            r.raise_for_status()
            
        except Exception:
            print('There was an error downloading from {}'.format(url))

        if well_formed:
            try:
                etree.fromstring(r.text)
            except Exception:
                print('Metadata record from {} not well-formed'.format(url))

        if fname[-4:] != '.xml':
            fname += '.xml'

        with open(fname, 'wt') as f:
            f.write(r.text)


def recordXpathContent(EvaluatedMetadataDF):
    """requires a dataframe with elements. Creates a vertical view of
    concept content for each record in the collection. Useful in the
    creation of json.
    """
    EvaluatedMetadataDF = EvaluatedMetadataDF.applymap(str)

    group_name = EvaluatedMetadataDF.groupby([
        'Collection', 'Record', 'XPath'], as_index=False)
    occurrenceMatrix = group_name['Content'].apply(
        lambda x: '%s' % ', '.join(x)).unstack().reset_index()

    occurrenceMatrix.columns.names = ['']

    #FILLvalues = 'No Content'
    #occurrenceMatrix = occurrenceMatrix.fillna(value=FILLvalues)
    occurrenceMatrix.reset_index()

    return(occurrenceMatrix)

def applyRecommendation(recElements, recommendationName, collection):

    # places for all the evaluated and analyzed data
    XpathEvaluated = os.path.join("..","data", recommendationName, collection + "_XpathEvaluated.csv.gz")
    EvaluatedDF = pd.read_csv(XpathEvaluated)

    # Use above dataframe and apply the xpathCounts and xpathOccurrence functions from MDeval for each recommendation


    
    RecommendationEvaluated = os.path.join("..","data", recommendationName, collection + '_' + recommendationName + 'Evaluated.csv.gz')
    #RecommendationCounts = os.path.join("../data/", collection + '_' + recommendationName + 'Counts.csv')
    RecommendationOccurrence = os.path.join("..","data", recommendationName, collection + '_' + recommendationName + 'Occurrence.csv')
    
   
    # Use the output of the evaluation transform and the piped string 
    # of all root paths to create a dataframe of just recommendation elements
    recElementsPattern = '|'.join(recElements)
    
    RecommendationDF = EvaluatedDF[EvaluatedDF['XPath'].str.contains(recElementsPattern)]
    
    RecommendationDF.to_csv(RecommendationEvaluated, index=False, compression='gzip')
                
    
    #XpathCounts(RecommendationDF, RecommendationCounts)
    
      # change order of rows to be meaningful for recommendation
    #RecommendationCountsDF = pd.read_csv(RecommendationCounts)
    CollectionRecRows = []
    CollectionRecRows.append(["Number of Records"])

    CollectionRecColumns = []
    CollectionRecColumns.append(["Collection","Record"])
    XpathOccurrence(RecommendationDF, collection, RecommendationOccurrence)
    
    RecommendationOccurrenceDF = pd.read_csv(RecommendationOccurrence)
    for element in recElements:

        # find the rows that match each element
        CollectionElements = list(RecommendationOccurrenceDF['XPath'])[1:]

        matchingElements = [CollectionElement for CollectionElement in CollectionElements if element in CollectionElement]

        #append the list to a master list that will be used to order the chart
        CollectionRecRows.append(matchingElements)
        CollectionRecColumns.append(matchingElements)

    CollectionRecRows = [item for sublist in CollectionRecRows for item in sublist]
    CollectionRecColumns = [item for sublist in CollectionRecColumns for item in sublist]
    from collections import OrderedDict
    CollectionRecRows = list(OrderedDict.fromkeys(CollectionRecRows))
    CollectionRecColumns = list(OrderedDict.fromkeys(CollectionRecColumns))
   
    #RecommendationCountsDF = RecommendationCountsDF[CollectionRecColumns]

    # write over the previous csv
    #RecommendationCountsDF.to_csv(RecommendationCounts, index=False, mode='w')
    
 
    # change order of rows to be meaningful for recommendation
    RecommendationOccurrenceDF = RecommendationOccurrenceDF.set_index('XPath')

    RecommendationOccurrenceDF = RecommendationOccurrenceDF.loc[CollectionRecRows]
    RecommendationOccurrenceDF = RecommendationOccurrenceDF.reset_index()

def XpathCounts(EvaluatedMetadataDF,
                DataDestination, to_csv=True):
    """XpathCounts requires a dataframe with xpath.The DF
    can created be localAllNodesEval, XMLeval(not accurate), or
    a simpleXpath. It is required for combineXpathCounts"""
    group_name = EvaluatedMetadataDF.groupby(
        ['Collection', 'Record', 'XPath'], as_index=False)
    XpathCountsDF = group_name.size().unstack().reset_index()
    XpathCountsDF = XpathCountsDF.fillna(0)
    pd.options.display.float_format = '{:,.0f}'.format

    if to_csv:
        lggr.info('Saving Xpath counts report to %s' % DataDestination)
        XpathCountsDF.to_csv(DataDestination, mode='w', index=False)

    return XpathCountsDF


def XpathOccurrence(EvaluatedMetadataDF, Collection,
                    DataDestination, to_csv=True):
    # xpath occurrence data product
    """requires a list of xpathOccurrence csv.
    It is required for CombinationSpreadsheet
    """
    DataDestinationDirectory = DataDestination[:DataDestination.rfind('/') + 1]
    os.makedirs(DataDestinationDirectory, exist_ok=True)
    group_name = EvaluatedMetadataDF.groupby(
        ['Record', 'XPath'], as_index=False)
    occurrenceMatrix = group_name.size().unstack().reset_index()
    occurrenceMatrix = occurrenceMatrix.fillna(0)
    occurrenceSum = occurrenceMatrix.sum()
    occurrenceCount = occurrenceMatrix[occurrenceMatrix != 0].count()

    result = pd.concat([occurrenceSum, occurrenceCount], axis=1).reset_index()
    result.insert(
        1, 'Collection', Collection)
    result.insert(4, 'CollectionOccurrence%', Collection)
    result.insert(4, 'AverageOccurrencePerRecord', Collection)
    result.columns = [
        'XPath', 'Collection', 'XPathCount', 'RecordCount',
        'AverageOccurrencePerRecord', 'CollectionOccurrence%'
    ]
    NumberOfRecords = result.at[0, 'XPathCount'].count('.xml')
    result['CollectionOccurrence%'] = result['RecordCount'] / NumberOfRecords
    result.at[0, 'XPathCount'] = NumberOfRecords
    result.at[0, 'XPath'] = 'Number of Records'
    result.at[0, 'CollectionOccurrence%'] = NumberOfRecords
    result['AverageOccurrencePerRecord'] = (
        result['XPathCount'] / NumberOfRecords)
    result[['AverageOccurrencePerRecord', 'CollectionOccurrence%']] = (
        result[['AverageOccurrencePerRecord',
                'CollectionOccurrence%']].astype(float)
    )
    result[["XPathCount", "RecordCount"]] = (
        result[["XPathCount", "RecordCount"]].astype(int)
    )
    result['AverageOccurrencePerRecord'] = (pd.Series([
        "{0:.2f}".format(val) for val in result['AverageOccurrencePerRecord']
    ], index=result.index))
    result.at[0, 'AverageOccurrencePerRecord'] = NumberOfRecords

    if to_csv:
        lggr.info('Saving XPath occurrence report to %s' % DataDestination)
        result.to_csv(DataDestination, mode='w', index=False)

    return result


def CombineXPathOccurrence(CollectionComparisons,
                           DataDestination, to_csv=True):
    """Using xpath occurrence data products, combine them and produce a
    collection occurrence% table with collections for columns and
    concepts for rows requires a list of xpathOccurrence csv.
    It is required for CombinationSpreadsheet
    """
    DataDestinationDirectory = DataDestination[:DataDestination.rfind('/') + 1]
    os.makedirs(DataDestinationDirectory, exist_ok=True)
    CombinedDF = pd.concat((pd.read_csv(f) for f in CollectionComparisons))
    CombinedPivotDF = CombinedDF.pivot(
        index='XPath', columns='Collection', values='CollectionOccurrence%')

    ConceptCountsDF = CombinedPivotDF.fillna(0)
    ConceptCountsDF.columns.names = ['']
    ConceptCountsDF = ConceptCountsDF.reset_index()

    line = ConceptCountsDF[ConceptCountsDF['XPath'] == 'Number of Records']
    ConceptCountsDF = pd.concat(
        [ConceptCountsDF[0:0], line,
         ConceptCountsDF[0:]]).reset_index(drop=True)
    ConceptCountsDF.drop(
        ConceptCountsDF.tail(1).index, inplace=True)

    if to_csv:
        lggr.info('Saving concept count report to %s' % DataDestination)
        ConceptCountsDF.to_csv(DataDestination, mode='w', index=False)

    return ConceptCountsDF



def CombinationSpreadsheet(xpathOccurrence, recommendationOccurrence,
                           RecommendationConcept, RecommendationGraph,
                           RecGraphLink,
                           DataDestination, AVGxpathOccurrence=None,
                           AVGrecommendationOccurrence=None,
                           recommendationCounts=None, xpathCounts=None,
                           recommendationOccurrence2=None,
                           RecommendationConcept2=None, RecommendationGraph2=None,
                           RecGraphLink2=None, AVGrecommendationOccurrence2=None,
                           recommendationCounts2=None):
    # create spreadsheet for an organization
    """requires each xpath and concept occurrence,
    csv for a organization
    (or any group of collections you want to compare)
    """

    lggr.info('Saving spreadsheet %s' % DataDestination)
    workbook = xlsxwriter.Workbook(DataDestination,
                                   {'strings_to_numbers': True})
    workbook.use_zip64()
    cell_format11 = workbook.add_format()
    cell_format11.set_num_format('0%')

    cell_format04 = workbook.add_format()
    cell_format04.set_num_format('0')
    cell_format05 = workbook.add_format()
    cell_format05.set_num_format('0.00')

    formatGreen = workbook.add_format(
        {'bg_color': '#C6EFCE', 'font_color': '#006100'})
    formatRed = workbook.add_format(
        {'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
    formatYellow = workbook.add_format(
        {'bg_color': '#FFEB9C', 'font_color': '#9C6500'})
    RecommendationConceptWS = workbook.add_worksheet(
        'BestPractices2004_Concepts')
    # RecommendationGraphWS = workbook.add_worksheet(
    #    'RecommendationGraph')
    # Insert an image with scaling.
    RecommendationConceptWS.write('A29', "Full Image")
    RecommendationConceptWS.write('B29', RecGraphLink)
    RecommendationConceptWS.insert_image('A30', RecommendationGraph, {'x_scale': .07, 'y_scale': .07})

    Reader = csv.reader(
        open(RecommendationConcept, 'r'), delimiter=',', quotechar='"')

    row_count = 0
    RecommendationConceptWS.set_row(0, None, cell_format04)
    RecommendationConceptWS.set_row(2, None, cell_format04)
    
    for row in Reader:
        for col in range(len(row)):
            RecommendationConceptWS.write(row_count, col, row[col])
            RecommendationConceptWS.set_column(col, col, 7, cell_format11)
        row_count += 1
    RecommendationConceptWS.set_column(0, 0, 20)
    RecommendationConceptWS.set_column(1, 1, 15)
    RecommendationConceptWS.set_column(2, 2, 20)
    RecommendationAnalysisWS = workbook.add_worksheet(
        'BestPractices2004_Elements')
    RecommendationAnalysisWS.set_column(2, 4, 12)
    recommendationoccurrenceWS = workbook.add_worksheet(
        'BestPractices2004_Occurrence')
    avgRecommendationOccurWS = workbook.add_worksheet(
            'BestPractices2004_AVGoccurrence')
    if recommendationCounts is not None:
        recommendationcounts = workbook.add_worksheet('BestPractices2004_Counts')
###################################################################
# if a second recommendation

    if recommendationOccurrence2 is not None:

        RecommendationConcept2WS = workbook.add_worksheet(
        'BestPractices2011_Concepts')
        # RecommendationGraphWS = workbook.add_worksheet(
        #    'RecommendationGraph')
        # Insert an image with scaling.
        RecommendationConcept2WS.write('A31', "Full Image")
        RecommendationConcept2WS.write('B31', RecGraphLink2)
        RecommendationConcept2WS.insert_image('A33', RecommendationGraph2, {'x_scale': .07, 'y_scale': .07})
        
        
        Reader = csv.reader(
            open(RecommendationConcept2, 'r'), delimiter=',', quotechar='"')

        row_count = 0
        RecommendationConcept2WS.set_row(0, None, cell_format04)
        RecommendationConcept2WS.set_row(2, None, cell_format04)
        
        for row in Reader:
            for col in range(len(row)):
                RecommendationConcept2WS.write(row_count, col, row[col])
                RecommendationConcept2WS.set_column(col, col, 7, cell_format11)
            row_count += 1
        RecommendationConcept2WS.set_column(0, 0, 20)
        RecommendationConcept2WS.set_column(1, 1, 15)
        RecommendationConcept2WS.set_column(2, 2, 20)
        RecommendationAnalysis2WS = workbook.add_worksheet(
            'BestPractices2011_Elements')
        RecommendationAnalysis2WS.set_column(2, 4, 12)
        recommendationoccurrence2WS = workbook.add_worksheet(
            'BestPractices2011_Occurrence')
        avgRecommendationOccur2WS = workbook.add_worksheet(
                'BestPractices2011_AVGoccurrence')
        if recommendationCounts2 is not None:
            recommendationCounts2 = workbook.add_worksheet('BestPractices2011_Counts')

        #######################################################################

        RecommendationAnalysis2WS.set_column('A:A', 70)
        RecommendationAnalysis2WS.set_column('B:B', 20)

        recommendationoccurrence2WS.set_column('A:A', 70)
        recommendationoccurrence2WS.hide()
        Reader = csv.reader(
            open(recommendationOccurrence2, 'r'), delimiter=',', quotechar='"')

        row_count = 0
        recommendationoccurrence2WS.set_row(1, None, cell_format04)
        for row in Reader:
            for col in range(len(row)):
                recommendationoccurrence2WS.write(
                    row_count, col, row[col])

                recommendationoccurrence2WS.set_column(
                    col, col, 15, cell_format11)
            row_count += 1
        Reader = csv.reader(
            open(recommendationOccurrence2, 'r'), delimiter=',', quotechar='"')

        row_count = 0
        for row in Reader:
            if Reader.line_num != 2:
                for col in range(1, len(row)):
                    RecommendationAnalysis2WS.write(
                        row_count + 9, col + 4, row[col], cell_format11
                    )

                for col in range(0, 1):
                    RecommendationAnalysis2WS.write(
                        row_count + 9, col, row[col], cell_format11)

                    Recommendationcell = xlsxwriter.utility.xl_rowcol_to_cell(
                        row_count + 9, 0)
                    formulaElementSimplifier = (
                        '=MID(' + Recommendationcell +
                        ',1+FIND("|",SUBSTITUTE(' + Recommendationcell +
                        ',"/","|",LEN(' + Recommendationcell + ')-LEN(SUBSTITUTE(' +
                        Recommendationcell + ',"/","")))),100)'
                    )
                    RecommendationAnalysis2WS.write(
                        row_count + 9, col + 1, formulaElementSimplifier, cell_format11
                    )
                row_count += 1

        avgRecommendationOccur2WS.set_column('A:A', 70)
        avgRecommendationOccur2WS.hide()
        
        if AVGrecommendationOccurrence2 is not None:

            Reader = csv.reader(
                open(AVGrecommendationOccurrence2, 'r'), delimiter=',', quotechar='"')
            row_count = 0
            avgRecommendationOccur2WS.set_row(1, None, cell_format04)
            for row in Reader:
                for col in range(len(row)):
                    avgRecommendationOccur2WS.write(
                        row_count, col, row[col])
                    avgRecommendationOccur2WS.set_column(col, col, 15, cell_format05)
        RecommendationAnalysis2WS.write('A2', 'Number of records')
        RecommendationAnalysis2WS.write('A3', 'Number of elements')
        RecommendationAnalysis2WS.write(
            'A4',
            'Number of recommendation elements'
        )
        RecommendationAnalysis2WS.write('A5', 'Recommendation focus')
        RecommendationAnalysis2WS.write('A6', 'Complete elements in the collection')
        RecommendationAnalysis2WS.write('A7', 'Complete recommendation elements in the collection')
        RecommendationAnalysis2WS.write(
            'A8', 'Recommendation completeness focus')
        RecommendationAnalysis2WS.write('A9', 'Upload Date')
        RecommendationAnalysis2WS.write('B1', 'Formulas')
        RecommendationAnalysis2WS.write('C1', 'MIN')
        RecommendationAnalysis2WS.write('D1', 'MAX')
        RecommendationAnalysis2WS.write('E1', 'AVG')
        RecommendationAnalysis2WS.write('B10', 'Element Name')
        RecommendationAnalysis2WS.write('C10', 'Collections')
        RecommendationAnalysis2WS.write('D10', 'Complete')
        RecommendationAnalysis2WS.write('E10', 'Partial')

        Reader = csv.reader(
            open(recommendationOccurrence2, 'r'), delimiter=',', quotechar='"')

        row_count = 0
        for row in Reader:
            for col in range(len(row) - 1):
                ElementTotal = xlsxwriter.utility.xl_rowcol_to_cell(5, col + 5)
                RecommendationElementTotal = xlsxwriter.utility.xl_rowcol_to_cell(6, col + 5)
                cell2 = xlsxwriter.utility.xl_rowcol_to_cell(0, col + 1)
                cell3 = xlsxwriter.utility.xl_rowcol_to_cell(2, col + 5)
                cell4 = xlsxwriter.utility.xl_rowcol_to_cell(3, col + 5)
                colRange = xlsxwriter.utility.xl_range(2, col + 1, 5000, col + 1)
                colRange2 = xlsxwriter.utility.xl_range(2, 5, 2, len(row) + 3)

                formula2 = '=COUNTIF(XpathOccurrence!' + colRange + ',">"&0)'
                RecommendationAnalysis2WS.write(2, col + 5, formula2)

                formula3 = '=COUNTIF(BestPractices2011_Occurrence!' + colRange + ',">"&0)'
                RecommendationAnalysis2WS.write(3, col + 5, formula3)

                formula4 = '='+cell4+'/'+cell3
                RecommendationAnalysis2WS.write(4, col + 5, formula4, cell_format11)

                formula5 = '=COUNTIF(XpathOccurrence!' + colRange + ',"=1")/'+cell3 
                RecommendationAnalysis2WS.write(5, col + 5, formula5, cell_format11)

                formula6 = '=COUNTIF(BestPractices2011_Occurrence!' + colRange + ',"=1")/'+cell3
                RecommendationAnalysis2WS.write(6, col + 5, formula6, cell_format11)

                formula7 = '='+RecommendationElementTotal+'/'+ElementTotal
                RecommendationAnalysis2WS.write(7, col + 5, formula7, cell_format11)

                formula1 = (
                    '=VLOOKUP("Number of Records",BestPractices2011_Occurrence!1:1048576,' +
                    str(col + 2) + ', False)'
                )
                RecommendationAnalysis2WS.write(1, col + 5, formula1, cell_format04)

                formula = '=BestPractices2011_Occurrence!' + '%s' % cell2
                RecommendationAnalysis2WS.write(0, col + 5, formula)
                dateFormula = (
                    '=LEFT(RIGHT(BestPractices2011_Occurrence!' + '%s' % cell2 +
                    ',LEN(BestPractices2011_Occurrence!' + '%s' % cell2 +
                    ')-FIND("_", BestPractices2011_Occurrence!' +
                    '%s' % cell2 + ')-1),FIND("_",BestPractices2011_Occurrence!' +
                    '%s' % cell2 + ')+1)'
                )
                RecommendationAnalysis2WS.write(8, col + 5, dateFormula)
                collectFormula = (
                    '=LEFT(BestPractices2011_Occurrence!' + '%s' % cell2 +
                    ',FIND("_",BestPractices2011_Occurrence!' + '%s' % cell2 + ')-1)'
                )

                RecommendationAnalysis2WS.write(9, col + 5, collectFormula)

            row_count += 1
        #######################################################################

        if recommendationCounts2 is not None:
            Reader = csv.reader(
                open(recommendationCounts2, 'r'), delimiter=',', quotechar='"')
            row_count = 0

            for row in Reader:
                for col in range(len(row)):
                    recommendationCounts2.write(
                        row_count, col, row[col], cell_format04)
                row_count += 1
            Reader = csv.reader(
                open(recommendationCounts2, 'r'), delimiter=',', quotechar='"')
            row_count = 0
            absRowCount = sum(1 for row in Reader)
            absColCount = len(next(csv.reader(
                open(recommendationCounts2, 'r'), delimiter=',', quotechar='"')))
            recommendationCounts2.autofilter(0, 0, absRowCount - 1, absColCount - 1)

        
        for row in range(1, 4):
            absColCount = len(next(csv.reader(
                open(recommendationOccurrence, 'r'), delimiter=',', quotechar='"'
            )))
            colRange4 = xlsxwriter.utility.xl_range(row, 5, row, 3 + absColCount)
            miniFormula = '=MIN(' + colRange4 + ')'
            RecommendationAnalysis2WS.write(row, 2, miniFormula, cell_format04)
            maxiFormula = '=MAX(' + colRange4 + ')'
            RecommendationAnalysis2WS.write(row, 3, maxiFormula, cell_format04)
            avgFormula = '=AVERAGE(' + colRange4 + ')'
            RecommendationAnalysis2WS.write(row, 4, avgFormula, cell_format04)

        for row in range(4, 8):
            absColCount = len(next(csv.reader(
                open(recommendationOccurrence, 'r'), delimiter=',', quotechar='"'
            )))
            colRange4 = xlsxwriter.utility.xl_range(row, 5, row, 3 + absColCount)
            miniFormula = '=MIN(' + colRange4 + ')'
            RecommendationAnalysis2WS.write(row, 2, miniFormula, cell_format11)
            maxiFormula = '=MAX(' + colRange4 + ')'
            RecommendationAnalysis2WS.write(row, 3, maxiFormula, cell_format11)
            avgFormula = '=AVERAGE(' + colRange4 + ')'
            RecommendationAnalysis2WS.write(row, 4, avgFormula, cell_format11)

        Reader = csv.reader(
            open(recommendationOccurrence2, 'r'), delimiter=',', quotechar='"'
        )
        absRowCount = sum(1 for row in Reader)
        absColCount = len(next(csv.reader(
            open(recommendationOccurrence2, 'r'), delimiter=',', quotechar='"'
        )))

        RecommendationAnalysis2WS.autofilter(9, 0, absRowCount + 7, absColCount + 3)
        recommendationoccurrence2WS.autofilter(
            0, 0, absRowCount - 2, absColCount - 1)
        avgRecommendationOccur2WS.autofilter(0, 0, absRowCount - 2, absColCount - 1)

        RecommendationAnalysis2WS.conditional_format(
            10, 5, absRowCount + 8, absColCount +
            3,
            {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': formatGreen}
        )
        RecommendationAnalysis2WS.conditional_format(
            10, 5, absRowCount + 8, absColCount + 3,
            {'type': 'cell', 'criteria': '=', 'value': 0, 'format': formatYellow}
        )
        RecommendationAnalysis2WS.conditional_format(
            10, 5, absRowCount + 8, absColCount + 3,
            {'type': 'cell', 'criteria': '=', 'value': -1, 'format': formatRed}
        )
        recommendationoccurrence2WS.conditional_format(
            2, 1, absRowCount - 1, absColCount - 1,
            {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': formatGreen}
        )
        recommendationoccurrence2WS.conditional_format(
            2, 1, absRowCount - 1, absColCount - 1,
            {'type': 'cell', 'criteria': '=', 'value': 0, 'format': formatYellow}
        )
        recommendationoccurrence2WS.conditional_format(
            2, 1, absRowCount - 1, absColCount - 1,
            {'type': 'cell', 'criteria': '=', 'value': -1, 'format': formatRed}
        )
        avgRecommendationOccur2WS.conditional_format(
            2, 1, absRowCount - 1, absColCount - 1,
            {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': formatGreen})
        avgRecommendationOccur2WS.conditional_format(
            2, 1, absRowCount - 1, absColCount - 1,
            {'type': 'cell', 'criteria': '=', 'value': 0, 'format': formatYellow})
        avgRecommendationOccur2WS.conditional_format(
            2, 1, absRowCount - 1, absColCount - 1,
            {'type': 'cell', 'criteria': '=', 'value': -1, 'format': formatRed})

        RecommendationConcept2WS.conditional_format(
            3, 3, 28, absColCount + 1,
            {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': formatGreen}
        )
        RecommendationConcept2WS.conditional_format(
            3, 3, 28, absColCount + 1,
            {'type': 'cell', 'criteria': '=', 'value': 0, 'format': formatYellow}
        )
        RecommendationConcept2WS.conditional_format(
            3, 3, 28, absColCount + 1,
            {'type': 'cell', 'criteria': '=', 'value': -1, 'format': formatRed}
        )
        RecommendationConcept2WS.conditional_format(
            1, 3, 1, absColCount - 1,
            {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': formatGreen}
        )
        RecommendationConcept2WS.conditional_format(
            1, 3, 1, absColCount - 1,
            {'type': 'cell', 'criteria': '=', 'value': 0, 'format': formatYellow}
        )
        RecommendationConcept2WS.conditional_format(
            1, 3, 1, absColCount - 1,
            {'type': 'cell', 'criteria': '=', 'value': -1, 'format': formatRed}
        )
        for row in range(10, absRowCount + 8):
            colRange5 = xlsxwriter.utility.xl_range(row, 5, row, absColCount + 3)
            numbCollectFormula = '=COUNTIF(' + colRange5 + ',">"&0)'
            CompleteCollectFormula = '=COUNTIF(' + colRange5 + ',"="&1)'
            GreatCollectFormula = '=COUNTIF(' + colRange5 + ',"<"&1)-COUNTIF('+ colRange5 + ',"=0")'
            RecommendationAnalysis2WS.write(row, 2, numbCollectFormula)
            RecommendationAnalysis2WS.write(row, 3, CompleteCollectFormula)
            RecommendationAnalysis2WS.write(row, 4, GreatCollectFormula)

###################################################################
    XpathAnalysisWS = workbook.add_worksheet('AllXpaths')
    xpathoccurrenceWS = workbook.add_worksheet('XpathOccurrence')
    avgXpathOccurWS = workbook.add_worksheet('AVGxpathOccurrence')
    if xpathCounts is not None:
        xpathcounts = workbook.add_worksheet('XpathCounts')
    XpathAnalysisWS.set_column('A:A', 70)
    XpathAnalysisWS.set_column('B:B', 20)
    recommendationoccurrenceWS.hide()
    xpathoccurrenceWS.hide()
    avgXpathOccurWS.hide()
    avgRecommendationOccurWS.hide()
    xpathoccurrenceWS.set_column('A:A', 70)

    Reader = csv.reader(
        open(xpathOccurrence, 'r'), delimiter=',', quotechar='"')

    row_count = 0
    xpathoccurrenceWS.set_row(1, None, cell_format04)
    for row in Reader:
        for col in range(len(row)):
            xpathoccurrenceWS.write(row_count, col, row[col])
            xpathoccurrenceWS.set_column(col, col, 15, cell_format11)
        row_count += 1

    Reader = csv.reader(
        open(xpathOccurrence, 'r'), delimiter=',', quotechar='"')

    row_count = 0
    for row in Reader:
        if Reader.line_num != 2:
            for col in range(1, len(row)):
                XpathAnalysisWS.write(
                    row_count + 9, col + 4, row[col], cell_format11
                )

            for col in range(0, 1):
                XpathAnalysisWS.write(row_count + 9, col, row[col], cell_format11)

                Xpathcell = xlsxwriter.utility.xl_rowcol_to_cell(row_count + 9, 0)
                formulaElementSimplifier = (
                    '=MID(' + Xpathcell +
                    ',1+FIND("|",SUBSTITUTE(' + Xpathcell +
                    ',"/","|",LEN(' + Xpathcell + ')-LEN(SUBSTITUTE(' +
                    Xpathcell + ',"/","")))),100)'
                )
                XpathAnalysisWS.write(
                    row_count + 9, col + 1, formulaElementSimplifier, cell_format11
                )
            row_count += 1
    if AVGxpathOccurrence is not None:
        avgXpathOccurWS.set_column('A:A', 70)

        Reader = csv.reader(
        open(AVGxpathOccurrence, 'r'), delimiter=',', quotechar='"')
    row_count = 0
    avgXpathOccurWS.set_row(1, None, cell_format04)
    for row in Reader:
        for col in range(len(row)):
            avgXpathOccurWS.write(row_count, col, row[col])
            avgXpathOccurWS.set_column(col, col, 15, cell_format05)

        for col in range(len(row) - 1):

            cell2 = xlsxwriter.utility.xl_rowcol_to_cell(0, col + 1)
            cell3 = xlsxwriter.utility.xl_rowcol_to_cell(2, col + 5)
            colRange = xlsxwriter.utility.xl_range(2, col + 1, 5000, col + 1)
            colRange2 = xlsxwriter.utility.xl_range(2, 5, 2, len(row) + 3)

            formula2 = '=COUNTIF(xpathOccurrence!' + colRange + ',">"&0)'
            XpathAnalysisWS.write(2, col + 5, formula2)

            formula6 = (
                '=COUNTIF(xpathOccurrence!' +
                colRange + ',">="&1)/' + '%s' % cell3
            )
            XpathAnalysisWS.write(6, col + 5, formula6, cell_format11)

            formula7 = (
                '=COUNTIFS(xpathOccurrence!' +
                colRange + ',">"&0,xpathOccurrence!' +
                colRange + ',"<"&1)/' + '%s' % cell3
            )
            XpathAnalysisWS.write(7, col + 5, formula7, cell_format11)

            formula1 = (
                '=VLOOKUP("Number of Records",xpathOccurrence!1:1048576,' +
                str(col + 2) + ', False)'
            )
            XpathAnalysisWS.write(1, col + 5, formula1, cell_format04)

            cell2 = xlsxwriter.utility.xl_rowcol_to_cell(0, col + 1)
            formula4 = '=SUM(xpathOccurrence!' + colRange + ')/' + '%s' % cell3
            XpathAnalysisWS.write(4, col + 5, formula4, cell_format11)

            formula5 = '=' + '%s' % cell3 + '/MAX(' + colRange2 + ')'
            XpathAnalysisWS.write(5, col + 5, formula5, cell_format11)
            formula = '=xpathOccurrence!' + '%s' % cell2
            XpathAnalysisWS.write(0, col + 5, formula)
            dateFormula = (
                '=LEFT(RIGHT(xpathOccurrence!' + '%s' % cell2 +
                ',LEN(xpathOccurrence!' + '%s' % cell2 +
                ')-FIND("_", xpathOccurrence!' +
                '%s' % cell2 + ')-1),FIND("_",xpathOccurrence!' +
                '%s' % cell2 + ')+1)'
            )
            XpathAnalysisWS.write(8, col + 5, dateFormula)
            collectFormula = (
                '=LEFT(xpathOccurrence!' + '%s' % cell2 +
                ',FIND("_",xpathOccurrence!' + '%s' % cell2 + ')-1)'
            )

            XpathAnalysisWS.write(9, col + 5, collectFormula)

        row_count += 1
    #######################################################################

    if xpathCounts is not None:
        Reader = csv.reader(
            open(xpathCounts, 'r'), delimiter=',', quotechar='"')
        row_count = 0

        for row in Reader:
            for col in range(len(row)):
                xpathcounts.write(row_count, col, row[col], cell_format04)
            row_count += 1
        Reader = csv.reader(
            open(xpathCounts, 'r'), delimiter=',', quotechar='"')
        row_count = 0
        absRowCount = sum(1 for row in Reader)
        absColCount = len(next(csv.reader(
            open(xpathCounts, 'r'), delimiter=',', quotechar='"')))
        xpathcounts.autofilter(0, 0, absRowCount - 1, absColCount - 1)

    XpathAnalysisWS.write('A2', 'Number of Records')
    XpathAnalysisWS.write('A3', 'Number of Elements / Attributes')
    #XpathAnalysisWS.write(
     #   'A4',
      #  'Coverage w/r to Repository (CR): \
     #number of elements / total number of elements'
    #)
    #XpathAnalysisWS.write('A5', 'Average Occurrence Rate')
    #XpathAnalysisWS.write('A6', 'Repository Completeness: Number of elements \
    #/ number of elements in most complete collection in repository')
    XpathAnalysisWS.write('A7', 'Complete Elements')
    #/ Total Number of elements in the collection')
    XpathAnalysisWS.write('A8', 'Partially Complete Elements')
    XpathAnalysisWS.write('A9', 'Upload Date')
    XpathAnalysisWS.write('C1', 'MIN')
    XpathAnalysisWS.write('D1', 'MAX')
    XpathAnalysisWS.write('E1', 'AVG')
    XpathAnalysisWS.write('B10', 'Element Name')
    XpathAnalysisWS.write('C10', 'Collections')
    XpathAnalysisWS.write('D10', 'Complete')
    XpathAnalysisWS.write('E10', 'Partial')

    for row in range(1, 3):
        absColCount = len(next(csv.reader(
            open(xpathOccurrence, 'r'), delimiter=',', quotechar='"'
        )))
        colRange4 = xlsxwriter.utility.xl_range(row, 5, row, 3 + absColCount)
        miniFormula = '=MIN(' + colRange4 + ')'
        XpathAnalysisWS.write(row, 2, miniFormula, cell_format04)
        maxiFormula = '=MAX(' + colRange4 + ')'
        XpathAnalysisWS.write(row, 3, maxiFormula, cell_format04)
        avgFormula = '=AVERAGE(' + colRange4 + ')'
        XpathAnalysisWS.write(row, 4, avgFormula, cell_format04)

    for row in range(6, 8):
        absColCount = len(next(csv.reader(
            open(xpathOccurrence, 'r'), delimiter=',', quotechar='"'
        )))
        colRange4 = xlsxwriter.utility.xl_range(row, 5, row, 3 + absColCount)
        miniFormula = '=MIN(' + colRange4 + ')'
        XpathAnalysisWS.write(row, 2, miniFormula, cell_format11)
        maxiFormula = '=MAX(' + colRange4 + ')'
        XpathAnalysisWS.write(row, 3, maxiFormula, cell_format11)
        avgFormula = '=AVERAGE(' + colRange4 + ')'
        XpathAnalysisWS.write(row, 4, avgFormula, cell_format11)

    Reader = csv.reader(
        open(xpathOccurrence, 'r'), delimiter=',', quotechar='"'
    )
    absRowCount = sum(1 for row in Reader)
    absColCount = len(next(csv.reader(
        open(xpathOccurrence, 'r'), delimiter=',', quotechar='"'
    )))

    XpathAnalysisWS.autofilter(9, 0, absRowCount + 7, absColCount + 3)
    xpathoccurrenceWS.autofilter(0, 0, absRowCount - 2, absColCount - 1)
    avgXpathOccurWS.autofilter(0, 0, absRowCount - 2, absColCount - 1)

    XpathAnalysisWS.conditional_format(
        10, 5, absRowCount + 8, absColCount +
        3,
        {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': formatGreen}
    )
    XpathAnalysisWS.conditional_format(
        10, 5, absRowCount + 8, absColCount + 3,
        {'type': 'cell', 'criteria': '=', 'value': 0, 'format': formatYellow}
    )
    XpathAnalysisWS.conditional_format(
        10, 5, absRowCount + 8, absColCount + 3,
        {'type': 'cell', 'criteria': '=', 'value': -1, 'format': formatRed}
    )
    xpathoccurrenceWS.conditional_format(
        2, 1, absRowCount - 1, absColCount - 1,
        {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': formatGreen}
    )
    xpathoccurrenceWS.conditional_format(
        2, 1, absRowCount - 1, absColCount - 1,
        {'type': 'cell', 'criteria': '=', 'value': 0, 'format': formatYellow}
    )
    xpathoccurrenceWS.conditional_format(
        2, 1, absRowCount - 1, absColCount - 1,
        {'type': 'cell', 'criteria': '=', 'value': -1, 'format': formatRed}
    )

    xpathoccurrenceWS.conditional_format(
        2, 1, absRowCount - 1, absColCount - 1,
        {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': formatGreen}
    )
    xpathoccurrenceWS.conditional_format(
        2, 1, absRowCount - 1, absColCount - 1,
        {'type': 'cell', 'criteria': '=', 'value': 0, 'format': formatYellow}
    )
    xpathoccurrenceWS.conditional_format(
        2, 1, absRowCount - 1, absColCount - 1,
        {'type': 'cell', 'criteria': '=', 'value': -1, 'format': formatRed}
    )


    avgXpathOccurWS.conditional_format(
        2, 1, absRowCount - 1, absColCount - 1,
        {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': formatGreen})
    avgXpathOccurWS.conditional_format(
        2, 1, absRowCount - 1, absColCount - 1,
        {'type': 'cell', 'criteria': '=', 'value': 0, 'format': formatYellow})
    avgXpathOccurWS.conditional_format(
        2, 1, absRowCount - 1, absColCount - 1,
        {'type': 'cell', 'criteria': '=', 'value': -1, 'format': formatRed})
    for row in range(10, absRowCount + 8):
        colRange5 = xlsxwriter.utility.xl_range(row, 5, row, absColCount + 3)
        numbCollectFormula = '=COUNTIF(' + colRange5 + ',">"&0)'
        CompleteCollectFormula = '=COUNTIF(' + colRange5 + ',"="&1)'
        GreatCollectFormula = '=COUNTIF(' + colRange5 + ',"<"&1)-COUNTIF('+ colRange5 + ',"=0")'
        XpathAnalysisWS.write(row, 2, numbCollectFormula)
        XpathAnalysisWS.write(row, 3, CompleteCollectFormula)
        XpathAnalysisWS.write(row, 4, GreatCollectFormula)

    #######################################################################
    Reader = csv.reader(
        open(xpathOccurrence, 'r'), delimiter=',', quotechar='"')

    row_count = 0
    for row in Reader:
        for col in range(len(row) - 1):

            cell2 = xlsxwriter.utility.xl_rowcol_to_cell(0, col + 1)
            cell3 = xlsxwriter.utility.xl_rowcol_to_cell(2, col + 5)
            colRange = xlsxwriter.utility.xl_range(2, col + 1, 5000, col + 1)
            colRange2 = xlsxwriter.utility.xl_range(2, 5, 2, len(row) + 3)


            formula1 = (
                '=VLOOKUP("Number of Records",xpathOccurrence!1:1048576,' +
                str(col + 2) + ', False)'
            )
            XpathAnalysisWS.write(1, col + 5, formula1, cell_format04)

            cell2 = xlsxwriter.utility.xl_rowcol_to_cell(0, col + 1)
            formula2 = '=COUNTIF(xpathOccurrence!' + colRange + ',">"&0)'
            XpathAnalysisWS.write(2, col + 5, formula2)
            formula = '=xpathOccurrence!' + '%s' % cell2
            XpathAnalysisWS.write(0, col + 5, formula)
            formula6 = (
                '=COUNTIF(xpathOccurrence!' +
                colRange + ',">="&1)/' + '%s' % cell3
            )
            XpathAnalysisWS.write(6, col + 5, formula6, cell_format11)

            formula7 = (
                '=COUNTIFS(xpathOccurrence!' +
                colRange + ',">"&0,xpathOccurrence!' +
                colRange + ',"<"&1)/' + '%s' % cell3
            )
            XpathAnalysisWS.write(7, col + 5, formula7, cell_format11)
            dateFormula = (
                '=LEFT(RIGHT(xpathOccurrence!' + '%s' % cell2 +
                ',LEN(xpathOccurrence!' + '%s' % cell2 +
                ')-FIND("_", xpathOccurrence!' +
                '%s' % cell2 + ')-1),FIND("__",xpathOccurrence!' +
                '%s' % cell2 + ')+1)'
            )
            XpathAnalysisWS.write(8, col + 5, dateFormula)
            collectFormula = (
                '=LEFT(xpathOccurrence!' + '%s' % cell2 +
                ',FIND("_",xpathOccurrence!' + '%s' % cell2 + ')-1)'
            )

            XpathAnalysisWS.write(9, col + 5, collectFormula)
    #######################################################################

    RecommendationAnalysisWS.set_column('A:A', 70)
    RecommendationAnalysisWS.set_column('B:B', 20)

    recommendationoccurrenceWS.set_column('A:A', 70)

    Reader = csv.reader(
        open(recommendationOccurrence, 'r'), delimiter=',', quotechar='"')

    row_count = 0
    recommendationoccurrenceWS.set_row(1, None, cell_format04)
    for row in Reader:
        for col in range(len(row)):
            recommendationoccurrenceWS.write(
                row_count, col, row[col])

            recommendationoccurrenceWS.set_column(
                col, col, 15, cell_format11)
        row_count += 1
    Reader = csv.reader(
        open(recommendationOccurrence, 'r'), delimiter=',', quotechar='"')

    row_count = 0
    for row in Reader:
        if Reader.line_num != 2:
            for col in range(1, len(row)):
                RecommendationAnalysisWS.write(
                    row_count + 9, col + 4, row[col], cell_format11
                )

            for col in range(0, 1):
                RecommendationAnalysisWS.write(
                    row_count + 9, col, row[col], cell_format11)

                Recommendationcell = xlsxwriter.utility.xl_rowcol_to_cell(
                    row_count + 9, 0)
                formulaElementSimplifier = (
                    '=MID(' + Recommendationcell +
                    ',1+FIND("|",SUBSTITUTE(' + Recommendationcell +
                    ',"/","|",LEN(' + Recommendationcell + ')-LEN(SUBSTITUTE(' +
                    Recommendationcell + ',"/","")))),100)'
                )
                RecommendationAnalysisWS.write(
                    row_count + 9, col + 1, formulaElementSimplifier, cell_format11
                )
            row_count += 1

    avgRecommendationOccurWS.set_column('A:A', 70)
    if AVGrecommendationOccurrence is not None:
        Reader = csv.reader(
            open(AVGrecommendationOccurrence, 'r'), delimiter=',', quotechar='"')
        row_count = 0
        avgRecommendationOccurWS.set_row(1, None, cell_format04)
        for row in Reader:
            for col in range(len(row)):
                avgRecommendationOccurWS.write(
                    row_count, col, row[col])
                avgRecommendationOccurWS.set_column(col, col, 15, cell_format05)
    RecommendationAnalysisWS.write('A2', 'Number of records')
    RecommendationAnalysisWS.write('A3', 'Number of elements')
    RecommendationAnalysisWS.write(
        'A4',
        'Number of recommendation elements'
    )
    RecommendationAnalysisWS.write('A5', 'Recommendation focus')
    RecommendationAnalysisWS.write('A6', 'Complete elements in the collection')
    RecommendationAnalysisWS.write('A7', 'Complete recommendation elements in the collection')
    RecommendationAnalysisWS.write(
        'A8', 'Recommendation completeness focus')
    RecommendationAnalysisWS.write('A9', 'Upload Date')
    RecommendationAnalysisWS.write('B1', 'Formulas')
    RecommendationAnalysisWS.write('C1', 'MIN')
    RecommendationAnalysisWS.write('D1', 'MAX')
    RecommendationAnalysisWS.write('E1', 'AVG')
    RecommendationAnalysisWS.write('B10', 'Element Name')
    RecommendationAnalysisWS.write('C10', 'Collections')
    RecommendationAnalysisWS.write('D10', 'Complete')
    RecommendationAnalysisWS.write('E10', 'Partial')

    Reader = csv.reader(
        open(recommendationOccurrence, 'r'), delimiter=',', quotechar='"')

    row_count = 0
    for row in Reader:
        for col in range(len(row) - 1):
            ElementTotal = xlsxwriter.utility.xl_rowcol_to_cell(5, col + 5)
            RecommendationElementTotal = xlsxwriter.utility.xl_rowcol_to_cell(6, col + 5)
            cell2 = xlsxwriter.utility.xl_rowcol_to_cell(0, col + 1)
            cell3 = xlsxwriter.utility.xl_rowcol_to_cell(2, col + 5)
            cell4 = xlsxwriter.utility.xl_rowcol_to_cell(3, col + 5)
            colRange = xlsxwriter.utility.xl_range(2, col + 1, 5000, col + 1)
            colRange2 = xlsxwriter.utility.xl_range(2, 5, 2, len(row) + 3)

            formula2 = '=COUNTIF(XpathOccurrence!' + colRange + ',">"&0)'
            RecommendationAnalysisWS.write(2, col + 5, formula2)

            formula3 = '=COUNTIF(BestPractices2004_Occurrence!' + colRange + ',">"&0)'
            RecommendationAnalysisWS.write(3, col + 5, formula3)

            formula4 = '='+cell4+'/'+cell3
            RecommendationAnalysisWS.write(4, col + 5, formula4, cell_format11)

            formula5 = '=COUNTIF(XpathOccurrence!' + colRange + ',"=1")/'+cell3 
            RecommendationAnalysisWS.write(5, col + 5, formula5, cell_format11)

            formula6 = '=COUNTIF(BestPractices2004_Occurrence!' + colRange + ',"=1")/'+cell3
            RecommendationAnalysisWS.write(6, col + 5, formula6, cell_format11)

            formula7 = '='+RecommendationElementTotal+'/'+ElementTotal
            RecommendationAnalysisWS.write(7, col + 5, formula7, cell_format11)

            formula1 = (
                '=VLOOKUP("Number of Records",BestPractices2004_Occurrence!1:1048576,' +
                str(col + 2) + ', False)'
            )
            RecommendationAnalysisWS.write(1, col + 5, formula1, cell_format04)

            formula = '=BestPractices2004_Occurrence!' + '%s' % cell2
            RecommendationAnalysisWS.write(0, col + 5, formula)
            dateFormula = (
                '=LEFT(RIGHT(BestPractices2004_Occurrence!' + '%s' % cell2 +
                ',LEN(BestPractices2004_Occurrence!' + '%s' % cell2 +
                ')-FIND("_", BestPractices2004_Occurrence!' +
                '%s' % cell2 + ')-1),FIND("_",BestPractices2004_Occurrence!' +
                '%s' % cell2 + ')+1)'
            )
            RecommendationAnalysisWS.write(8, col + 5, dateFormula)
            collectFormula = (
                '=LEFT(BestPractices2004_Occurrence!' + '%s' % cell2 +
                ',FIND("_",BestPractices2004_Occurrence!' + '%s' % cell2 + ')-1)'
            )

            RecommendationAnalysisWS.write(9, col + 5, collectFormula)

        row_count += 1
    #######################################################################

    if recommendationCounts is not None:
        Reader = csv.reader(
            open(recommendationCounts, 'r'), delimiter=',', quotechar='"')
        row_count = 0

        for row in Reader:
            for col in range(len(row)):
                recommendationcounts.write(
                    row_count, col, row[col], cell_format04)
            row_count += 1
        Reader = csv.reader(
            open(recommendationCounts, 'r'), delimiter=',', quotechar='"')
        row_count = 0
        absRowCount = sum(1 for row in Reader)
        absColCount = len(next(csv.reader(
            open(recommendationCounts, 'r'), delimiter=',', quotechar='"')))
        recommendationcounts.autofilter(0, 0, absRowCount - 1, absColCount - 1)

    
    for row in range(1, 4):
        absColCount = len(next(csv.reader(
            open(recommendationOccurrence, 'r'), delimiter=',', quotechar='"'
        )))
        colRange4 = xlsxwriter.utility.xl_range(row, 5, row, 3 + absColCount)
        miniFormula = '=MIN(' + colRange4 + ')'
        RecommendationAnalysisWS.write(row, 2, miniFormula, cell_format04)
        maxiFormula = '=MAX(' + colRange4 + ')'
        RecommendationAnalysisWS.write(row, 3, maxiFormula, cell_format04)
        avgFormula = '=AVERAGE(' + colRange4 + ')'
        RecommendationAnalysisWS.write(row, 4, avgFormula, cell_format04)

    for row in range(4, 8):
        absColCount = len(next(csv.reader(
            open(recommendationOccurrence, 'r'), delimiter=',', quotechar='"'
        )))
        colRange4 = xlsxwriter.utility.xl_range(row, 5, row, 3 + absColCount)
        miniFormula = '=MIN(' + colRange4 + ')'
        RecommendationAnalysisWS.write(row, 2, miniFormula, cell_format11)
        maxiFormula = '=MAX(' + colRange4 + ')'
        RecommendationAnalysisWS.write(row, 3, maxiFormula, cell_format11)
        avgFormula = '=AVERAGE(' + colRange4 + ')'
        RecommendationAnalysisWS.write(row, 4, avgFormula, cell_format11)

    Reader = csv.reader(
        open(recommendationOccurrence, 'r'), delimiter=',', quotechar='"'
    )
    absRowCount = sum(1 for row in Reader)
    absColCount = len(next(csv.reader(
        open(recommendationOccurrence, 'r'), delimiter=',', quotechar='"'
    )))

    RecommendationAnalysisWS.autofilter(9, 0, absRowCount + 7, absColCount + 3)
    recommendationoccurrenceWS.autofilter(
        0, 0, absRowCount - 2, absColCount - 1)
    avgRecommendationOccurWS.autofilter(0, 0, absRowCount - 2, absColCount - 1)

    RecommendationAnalysisWS.conditional_format(
        10, 5, absRowCount + 8, absColCount +
        3,
        {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': formatGreen}
    )
    RecommendationAnalysisWS.conditional_format(
        10, 5, absRowCount + 8, absColCount + 3,
        {'type': 'cell', 'criteria': '=', 'value': 0, 'format': formatYellow}
    )
    RecommendationAnalysisWS.conditional_format(
        10, 5, absRowCount + 8, absColCount + 3,
        {'type': 'cell', 'criteria': '=', 'value': -1, 'format': formatRed}
    )
    recommendationoccurrenceWS.conditional_format(
        2, 1, absRowCount - 1, absColCount - 1,
        {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': formatGreen}
    )
    recommendationoccurrenceWS.conditional_format(
        2, 1, absRowCount - 1, absColCount - 1,
        {'type': 'cell', 'criteria': '=', 'value': 0, 'format': formatYellow}
    )
    recommendationoccurrenceWS.conditional_format(
        2, 1, absRowCount - 1, absColCount - 1,
        {'type': 'cell', 'criteria': '=', 'value': -1, 'format': formatRed}
    )
    avgRecommendationOccurWS.conditional_format(
        2, 1, absRowCount - 1, absColCount - 1,
        {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': formatGreen})
    avgRecommendationOccurWS.conditional_format(
        2, 1, absRowCount - 1, absColCount - 1,
        {'type': 'cell', 'criteria': '=', 'value': 0, 'format': formatYellow})
    avgRecommendationOccurWS.conditional_format(
        2, 1, absRowCount - 1, absColCount - 1,
        {'type': 'cell', 'criteria': '=', 'value': -1, 'format': formatRed})

    RecommendationConceptWS.conditional_format(
        3, 3, 28, absColCount + 1,
        {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': formatGreen}
    )
    RecommendationConceptWS.conditional_format(
        3, 3, 28, absColCount + 1,
        {'type': 'cell', 'criteria': '=', 'value': 0, 'format': formatYellow}
    )
    RecommendationConceptWS.conditional_format(
        3, 3, 28, absColCount + 1,
        {'type': 'cell', 'criteria': '=', 'value': -1, 'format': formatRed}
    )
    RecommendationConceptWS.conditional_format(
        1, 3, 1, absColCount - 1,
        {'type': 'cell', 'criteria': '>=', 'value': 1, 'format': formatGreen}
    )
    RecommendationConceptWS.conditional_format(
        1, 3, 1, absColCount - 1,
        {'type': 'cell', 'criteria': '=', 'value': 0, 'format': formatYellow}
    )
    RecommendationConceptWS.conditional_format(
        1, 3, 1, absColCount - 1,
        {'type': 'cell', 'criteria': '=', 'value': -1, 'format': formatRed}
    )
    for row in range(10, absRowCount + 8):
        colRange5 = xlsxwriter.utility.xl_range(row, 5, row, absColCount + 3)
        numbCollectFormula = '=COUNTIF(' + colRange5 + ',">"&0)'
        CompleteCollectFormula = '=COUNTIF(' + colRange5 + ',"="&1)'
        GreatCollectFormula = '=COUNTIF(' + colRange5 + ',"<"&1)-COUNTIF('+ colRange5 + ',"=0")'
        RecommendationAnalysisWS.write(row, 2, numbCollectFormula)
        RecommendationAnalysisWS.write(row, 3, CompleteCollectFormula)
        RecommendationAnalysisWS.write(row, 4, GreatCollectFormula)

    #######################################################################
    
    #######################################################################
    workbook.close()


def WriteToGoogle(SpreadsheetLocation, folderID=None, Convert=None, Link=None):
    """
    Upload files to Google Drive. Requires 
    """
    
    client_json = '../scripts/client_secrets.json'

    GoogleAuth.DEFAULT_SETTINGS['client_config_file'] = (client_json)

    gauth = GoogleAuth()
    # Try to load saved client credentials
    mycred_file = '../scripts/mycreds.txt'

    gauth.LoadCredentialsFile(mycred_file)
    # if not creds or creds.invalid:

    if gauth.credentials is None:
        # Authenticate if they're not there
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        # Refresh them if expired
        gauth.Refresh()

    else:
        # Initialize the saved creds
        gauth.Authorize()
# Save the current credentials to a file
    gauth.SaveCredentialsFile(mycred_file)

    drive = GoogleDrive(gauth)

    SpreadsheetName = SpreadsheetLocation.rsplit('/', 1)[-1]
    SpreadsheetName = SpreadsheetName[:-5]
    if folderID is not None:
        test_file = drive.CreateFile({'title': SpreadsheetName,
            "parents": [{"kind": "drive#fileLink", "id": folderID}]})
    else:
        test_file = drive.CreateFile(
            {'title': SpreadsheetName, "parents": [{"kind": "drive#fileLink"}]})

    test_file.SetContentFile(SpreadsheetLocation)
    if Convert is None:
        test_file.Upload({'convert': False})
    else:
        test_file.Upload({'convert': True})

    # Insert the permission.
    permission = test_file.InsertPermission(
        {'type': 'anyone', 'value': 'anyone', 'role': 'reader'})

    hyperlink = (test_file['alternateLink'])  # Display the sharable link.

    if Link is True:
        return hyperlink

    else:
        ReportURLstring = '<a href="' + str(hyperlink) + '">' + SpreadsheetName + '</a>'
        display(HTML(ReportURLstring))  # Display the sharable link.


def crop(image_path, coords, saved_location):
    """
    @param image_path: The path to the image to edit
    @param coords: A tuple of x/y coordinates (x1, y1, x2, y2)
    @param saved_location: Path to save the cropped image
    """
    image_obj = Image.open(image_path)
    cropped_image = image_obj.crop(coords)
    cropped_image.save(saved_location)


def Site_ttConceptAnalysis(Site, recommendationName, RecDict, LevelOrder, ConceptOrder, ElementOrder, YearsInvestigated):
    recMD = ['RecConcept',
             'RecLevel',
             'RecElement']
     # use a sites recommendation elements occurrence table, and add some columns for metadata about the recommendation
    recOccurDF = pd.read_csv(os.path.join("..","data", recommendationName, Site+"_" + recommendationName + "Occurrence.csv"))
    recOccurDF.insert(0, "RecElement", 0, allow_duplicates=False)
    recOccurDF.insert(0, "RecLevel", 0, allow_duplicates=False)    
    recOccurDF.insert(0, "RecConcept", 0, allow_duplicates=False)
    ''' 
    use the RecDict to look at the XPath column and for each key that matches part of any cell,
    write the value into the same row in the recOccurDF
    '''
    recOccurDF['RecElement'] = recOccurDF['XPath'].apply(lambda x: [value for key, value in RecDict.items() if key in x][0] )
    # create a list to order the columns with
    columnOrder = list(recOccurDF)
    # don't need xpaths any more
    columnOrder.remove('XPath')

    ''' 
    create a pivot table that leverages the dataframe recOccurDF's column for recommendation elements 
    and assigns the highest percentage any of the xpaths of the child elements to that row for a particular year
    '''
    radarElements = pd.pivot_table(recOccurDF, index='RecElement', columns=None, aggfunc='max').reindex(ElementOrder).reset_index()
    radarElements = radarElements[columnOrder]
   
    # fill in the metadata about concepts and recommendation levels
    radarElements['RecConcept'] = pd.Series(ConceptOrder)
    radarElements['RecLevel'] = pd.Series(LevelOrder)
    radarElements = radarElements.fillna(value=0.0)
    lineConcepts = radarElements
     # remove the site name from the column
    radarElements = radarElements.rename(columns={col: col.split('__')[-1] for col in radarElements.columns})
    # create recommendation concept csv
    #lineConcepts = lineConcepts.drop(['RecElement','RecLevel'], axis=1)
    lineConcepts.loc[-1] = lineConcepts.iloc[1:,:].mean(axis=0, numeric_only=True)
    lineConcepts.index = lineConcepts.index + 1  # shifting index
    lineConcepts.fillna('Average Completeness', inplace=True)
    lineConcepts = lineConcepts.sort_index()
    lineConcepts.to_csv(os.path.join('..','data', recommendationName, Site+'_' + recommendationName + 'Complete.csv'), index=False)
    
    # remove the site name from the column
    lineConcepts = lineConcepts.rename(columns={col: col.split('__')[-1] for col in lineConcepts.columns})
    lineConcepts.to_csv(os.path.join('..','data', recommendationName, Site+'_' + recommendationName + 'Completeness.csv'), index=False)

    # create new version of concept occurrence table
    radarList = list(radarElements)
    difference = list(set(YearsInvestigated) - set(radarList[3:]))
    for year in difference:
        radarElements.insert(0, year, 0, allow_duplicates=False) 
    RecOccurDFcols = recMD + YearsInvestigated
    radarElements = radarElements[RecOccurDFcols]
    '''
    Take the occurrence of the conceptual elements from each site's pivot table and plot each years output
    on a radar chart of 0 to 1 with each RecElement as an axis and the occurrence of records the percentage of color along that axis.
    '''
    # create a structure to add data to.
    data = []
    fig = tools.make_subplots(rows=14, cols=1, print_grid=False)
    count = 0
    # add the data from each year to a subplot.
    for year in YearsInvestigated: #collectionsToProcess
        count = count + 1
        data.append(go.Scatterpolar(
            name = year, 
            mode = 'lines', 
            r = radarElements[year].tolist()[1:],
            theta = radarElements['RecElement'].tolist()[1:],
            line = dict(width = 50), #, shape = 'spline', smoothing = 1.3),
            #opacity = .75,
            fill = 'toself',
            #fillcolor = '',
            connectgaps = False,
            subplot = 'polar'+year
        ))

        
    fig.add_traces(data)
    
    layout = {
    'polar2005': dict(

      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2006': dict(

      
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2007': dict(

      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2008': dict(

      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2009': dict(

      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2010': dict(

      
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2011': dict(

      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2012': dict(

      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2013': dict(

      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2014': dict(

      
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2015': dict(

      
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2016': dict(

      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2017': dict(

      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2018': dict(

      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'showlegend': False,
    "height": 1200, "width": 16800, "autosize": False, "title": Site + recommendationName + 'Completeness 2005-2018'    
}
    
# create a description of the placement of each subplot    
    layout2 = {
    'polar2005': dict(
      domain = dict(
        x = [0, 1],
        y = [.96, 1]
      ),        
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2006': dict(
      domain = dict(
        x = [0, 1],
        y = [0.89, 1]
      ),
      
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2007': dict(
      domain = dict(
        x = [0, 1],
        y = [0.818, 1]
      ),
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2008': dict(
      domain = dict(
        x = [0, 1],
        y = [0.746, 1]
      ),
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2009': dict(
      domain = dict(
        x = [0, 1],
        y = [0.675, 1]
      ),
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2010': dict(
      domain = dict(
        x = [0, 1],
        y = [0.603, 1]
      ),
      
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2011': dict(
      domain = dict(
        x = [0, 1],
        y = [0.531, 1]
      ),
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2012': dict(
      domain = dict(
        x = [0, 1],
        y = [0.460, 1]
      ),
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2013': dict(
      domain = dict(
        x = [0, 1],
        y = [0.388, 1]
      ),
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2014': dict(
      domain = dict(
        x = [0, 1],
        y = [0.317, 1]
      ),
      
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2015': dict(
      domain = dict(
        x = [0, 1],
        y = [0.245, 1]
      ),
      
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2016': dict(
      domain = dict(
        x = [0, 1],
        y = [0.174, 1]
      ),
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2017': dict(
      domain = dict(
        x = [0, 1],
        y = [0.103, 1]
      ),
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'polar2018': dict(
      domain = dict(
        x = [0, 1],
        y = [0.029, 1]
      ),
      radialaxis = dict(
        angle = 0
      ),
      angularaxis = dict(
        direction = "clockwise",
        period = 6
      )
    ),
    'showlegend': False,
    "height": 32700, "width": 1200, "autosize": False    
}
    fig2 = {'data':data,'layout':layout2}

    
    pio.write_image(fig2, os.path.join('..','data', recommendationName, Site + recommendationName + '_bigPict_.png'))

    fig = {'data':data,'layout':layout}
    
    pio.write_image(fig, os.path.join('..','data', recommendationName, Site + '_' + recommendationName + '_.png'))

    crop(os.path.join('..','data', recommendationName, Site+ recommendationName + '_bigPict_.png'), (0, 0, 1200, 16600), os.path.join('..','data', recommendationName, Site+ recommendationName + '_bigPicture_.png'))
    os.remove(os.path.join('..','data', recommendationName, Site+ recommendationName + '_bigPict_.png'))


def CombineAppliedRecommendation(Site, recElements, recommendationName, RecommendationOccurrenceToCombine, RecommendationcountsToCombine=None):
    # places for all the combined data

    RecommendationOccurrence = os.path.join("..", "data", recommendationName, "combinedCollections" + '_' + recommendationName + 'Occurrence.csv')
    RecommendationConcept = os.path.join('..','data', recommendationName, "combinedCollections" + '_' + recommendationName + 'Completeness.csv')
    #RecommendationGraph = os.path.join('..','data', recommendationName, "combinedCollections" + '_' + recommendationName + '_.png')

    if RecommendationcountsToCombine is not None:
        RecommendationCounts = os.path.join("..", "data", recommendationName, Site + '_' + recommendationName + 'Counts.csv')
       
        CombineXPathCounts(RecommendationcountsToCombine, RecommendationCounts)
        # combine xpathoccurrence from a specfic site for each year
        
        RecommendationCountsDF = pd.read_csv(RecommendationCounts)
    
    CombineXPathOccurrence(RecommendationOccurrenceToCombine,
                           RecommendationOccurrence, to_csv=True)
    RecommendationOccurrenceDF = pd.read_csv(RecommendationOccurrence)
    # change order of rows to be meaningful for recommendation
    CollectionRecRows = []
    CollectionRecRows.append(["Number of Records"])

    CollectionRecColumns = []
    CollectionRecColumns.append(["Collection","Record"])
    for element in recElements:

        # find the rows that match each element
        CollectionElements = list(RecommendationOccurrenceDF['XPath'])[1:]

        matchingElements = [CollectionElement for CollectionElement in CollectionElements if element in CollectionElement]

        #append the list to a master list that will be used to order the chart
        CollectionRecRows.append(matchingElements)
        CollectionRecColumns.append(matchingElements)

    CollectionRecRows = [item for sublist in CollectionRecRows for item in sublist]
    CollectionRecColumns = [item for sublist in CollectionRecColumns for item in sublist]
    from collections import OrderedDict
    CollectionRecRows = list(OrderedDict.fromkeys(CollectionRecRows))
    CollectionRecColumns = list(OrderedDict.fromkeys(CollectionRecColumns))
    if RecommendationcountsToCombine is not None:
        RecommendationCountsDF = RecommendationCountsDF[CollectionRecColumns]
    
    # change order of rows to be meaningful for recommendation
    RecommendationOccurrenceDF = RecommendationOccurrenceDF.set_index('XPath')

    RecommendationOccurrenceDF = RecommendationOccurrenceDF.loc[CollectionRecRows]
    RecommendationOccurrenceDF = RecommendationOccurrenceDF.reset_index()
    
    # write over the previous csv
    RecommendationOccurrenceDF.to_csv(RecommendationOccurrence, index=False, mode='w')


def Collection_ConceptAnalysis(Site, recommendationName, RecDict, LevelOrder, ConceptOrder, ElementOrder, YearsInvestigated):
    recMD = ['RecConcept',
             'RecLevel',
             'RecElement']
     # use a sites recommendation elements occurrence table, and add some columns for metadata about the recommendation
    recOccurDF = pd.read_csv(os.path.join("..","data", recommendationName, "combinedCollections"+"_" + recommendationName + "Occurrence.csv"))
    recOccurDF.insert(0, "RecElement", 0, allow_duplicates=False)
    recOccurDF.insert(0, "RecLevel", 0, allow_duplicates=False)    
    recOccurDF.insert(0, "RecConcept", '', allow_duplicates=False)
    ''' 
    use the RecDict to look at the XPath column and for each key that matches part of any cell,
    write the value into the same row in the recOccurDF
    '''
    recOccurDF['RecElement'] = recOccurDF['XPath'].apply(lambda x: [value for key, value in RecDict.items() if key in x][0] )
    # create a list to order the columns with
    columnOrder = list(recOccurDF)
    # don't need xpaths any more
    columnOrder.remove('XPath')

    ''' 
    create a pivot table that leverages the dataframe recOccurDF's column for recommendation elements 
    and assigns the highest percentage any of the xpaths of the child elements to that row for a particular year
    '''
    radarElements = pd.pivot_table(recOccurDF, index='RecElement', columns=None, aggfunc='max').reindex(ElementOrder).reset_index()
    radarElements = radarElements[columnOrder]
   
    # fill in the metadata about concepts and recommendation levels
    radarElements['RecConcept'] = pd.Series(ConceptOrder)
    radarElements['RecLevel'] = pd.Series(LevelOrder)
    radarElements = radarElements.fillna(value=0.0)
    lineConcepts = radarElements
     # remove the site name from the column
    #radarElements = radarElements.rename(columns={col: col.split('__')[-1] for col in radarElements.columns})
    # create recommendation concept csv
    #lineConcepts = lineConcepts.drop(['RecElement','RecLevel'], axis=1)
    lineConcepts.loc[-1] = lineConcepts.iloc[1:,:].mean(axis=0, numeric_only=True)
    lineConcepts.index = lineConcepts.index + 1  # shifting index
    lineConcepts.fillna('Average Completeness', inplace=True)
    lineConcepts = lineConcepts.sort_index()
    lineConcepts.to_csv(os.path.join('..','data', recommendationName, "combinedCollections"+'_' + recommendationName + 'Complete.csv'), index=False)
    
    # remove the site name from the column
    lineConcepts = lineConcepts.rename(columns={col: col.split('__')[-1] for col in lineConcepts.columns})
    lineConcepts.to_csv(os.path.join('..','data', recommendationName, "combinedCollections"+'_' + recommendationName + 'Completeness.csv'), index=False)

    # create new version of concept occurrence table
    radarList = list(radarElements)
    difference = list(set(YearsInvestigated) - set(radarList[3:]))
    for year in difference:
        radarElements.insert(0, year, 0, allow_duplicates=False) 
    RecOccurDFcols = recMD + YearsInvestigated
    radarElements = radarElements[RecOccurDFcols]
    '''
    Take the occurrence of the conceptual LTER elements from each site's pivot table and plot each years output
    on a radar chart of 0 to 1 with each RecElement as an axis and the occurrence of records the percentage of color along that axis.
    '''
    # create a structure to add data to.
    
    colorList = ['#1f77b4','#ff7f0e','#2ca02c','#d62728','#9467bd',
                 '#8c564b','#e377c2','#7f7f7f','#bcbd22','#17becf']
    
    count = 0
    # add the data from each year to a subplot.
    for year in YearsInvestigated:
        data = [go.Scatterpolar(
                    name = year, 
                    mode = 'lines', 
                    r = radarElements[year].tolist()[1:],
                    theta = radarElements['RecElement'].tolist()[1:],
                    line = dict(width = 10, color = colorList[count]),
                    opacity = .75,
                    fill = 'tonext',
                    fillcolor = colorList[count],
                    connectgaps = False,
                    subplot = 'polar',
                    text = radarElements[year][1],
                    textposition='middle center'
                )]
        layout = {
            'polar': dict(      
              radialaxis = dict(
                angle = 0
              ),
              angularaxis = dict(
                direction = "clockwise",
                period = 6
              ), hole =.20
            ),
            'showlegend': False,
            "height": 1300, "width": 1300, "autosize": False, 
            "title": radarElements[year][1], #'xanchor': 'center', 'yanchor': 'middle'   
        }

        fig = {'data':data,'layout':layout}

        pio.write_image(fig, os.path.join('..','data', recommendationName, year + '_' + recommendationName + '_.png'))

        count = count + 1
        if count is 10: 
            count = 0 

    imagesToCombine = [os.path.join("../data/FAIR", name) for name in os.listdir("../data/FAIR") if name.endswith('_.png') ]
    images = list(map(Image.open, imagesToCombine))
    widths, heights = zip(*(i.size for i in images))

    total_width = sum(widths)
    max_height = max(heights)

    new_im = Image.new('RGB', (total_width, max_height))

    x_offset = 0
    for im in images:
      new_im.paste(im, (x_offset,0))
      x_offset += im.size[0]

    new_im.save(os.path.join('..','data', recommendationName, 'combinedCollections_' + recommendationName + '_.png'))
    
        #im = Image.open(os.path.join('..','data', recommendationName, Site.upper() + '_' + year + '_' + recommendationName + '_.png'))
        #helvetica = ImageFont.truetype("/Library/Fonts/Arial.ttf", 12)
        #d = ImageDraw.Draw(im)

        #location = (600, 600)
        #text_color = (0, 0, 0)
        #d.text(location, str(round(radarElements[year][1],2)*100)+"%", fill=text_color)

        #im.save(os.path.join('..','data', recommendationName, Site.upper() + '_' + year + '_' + recommendationName + '_.png'))
        
        


