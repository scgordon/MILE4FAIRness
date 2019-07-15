# Metadata Improvement Lab at ESIP 4: Determining FAIR

A repository designed to facilitate exploration of what makes metadata collections FAIR from around ESIP's interdisciplinary community.

## Welcome

This repository is reproducible through **Jupyter Notebook**: documents that can contain cells of executable code, equations, visualizations, and narrative text. It's like having a single document that handles word processing (such as  Word), math functions (such as Excel), image generation and display, and an interface for coding.

The name **Jupyter** refers to the three coding languages, **Julia, Python, and R**, that are pillars of the modern scientific world. 

For this workshop, we are using Google Colaboratory which is a Jupyter notebook environment that requires no setup to use.

####  Overview of workshop session
In the fourth installment of the Metadata Improvement Lab, participants will utilize Python, XSL, and Jupyter Notebooks to determine if metadata collections contain the concepts needed to be FAIR. Participants will be able to utilize their own metadata, regardless of standard or choose from many sample collections from ESIP member organizations. Participants can load as many metadata collections as they would like to compare. 

No coding experience will be needed, though a basic understanding of XML will be helpful. A step by step set up for using Google Colaboratory, a Jupyter based web accessible computational environment, will be given. Participants will only need a Google account and a connected web browser to access and run the repository which will allow them to create a shape visualization that describes the fitness of their metadata’s FAIRness. No changes will be made to the device or account used. Participants may also import the workshop repository into their own Jupyter environment.

Since there are many ideas of what it means to be FAIR, this workshop will allow participants to work together or on their own to create a recommendation using Google Docs to facilitate collaboration. During the workshop we will discuss a draft of what FAIR means for EML producing membernodes that was compiled during a workshop this March at DataONE. The Documentation Cluster has built many wiki pages containing recommendations and the XPaths needed in many popular metadata standards, which will aid in the creation of a FAIR recommendation that works for the many standards used throughout ESIP’s member organizations. 

The recommendation will then be applied to the collections that participants have chosen to analyze. The workshop framework is highly portable and reusable, even including the generation of the raw data needed to evaluate the content of the metadata, though only the structure of documents will be utilized in this workshop. A report on the outcomes of the analysis will be created as a sharable Google Sheet. The report generated allows for comparison of collections, so that improvement can be measured, documented and visualized. 

* [Slides](https://schd.ws/hosted_files/2018esipsummermeeting/ab/MILESsessionOverview.pptx)

Your Python environment requires the following:

* [python](https://python.org) >=3.6

* [pandas]()
* [csv]()
* [gzip]()
* [os]()
* [requests]()
* [xlsxwriter]()
* [pydrive]()
* [lxml]()
* [sys]()
* [logging]()
* [IPython.core.display]()
* [shutil]()
* [itertools]()
* [subprocess]()
* [plotly]() >=3.8


This workshop has been tested in [JupyterLab](https://jupyter.org) >= 4.4.0 and Google Colaboratory.

## Workshop

Time to dive in!

Click this link to get started: [determineFAIRness.ipynb](https://colab.research.google.com/github/scgordon/MILE4FAIRness/blob/master/notebooks/determineFAIRness.ipynb) 

### Notebooks

##### [Determine FAIRness Notebook](./notebook/determineFAIRness.ipynb)
* Create environment
* Upload metadata
* Add recommendation
* Evaluate, analyze, and report on FAIRness

##### [Compile Collection](./notebook/compileCollections.ipynb)
* where the data was retrieved from
* why we had to scrub the data
* how the data was normalized

## Creating a Recommendation Resources
http://wiki.esipfed.org/index.php/Data_Discovery_(FGDC)

##### Additional resources for further exploration
* [Google Colaboratory FAQs](https://research.google.com/colaboratory/faq.html)
* [About Jupyter](https://jupyter.org/)
* [Google Colaboratory](https://colab.research.google.com/notebook#create=true&language=python3)
###### tutorials for self exploration
* [Colaboratory Getting Started](https://colab.research.google.com/notebooks/welcome.ipynb)
* [Colaboratory Tutorial](https://medium.com/@rohansingh_46766/getting-started-with-google-colaboratory-57b4863d4d7d)




