# Hi Devs!!!

In order to develop and test Spyder you will need some python packages in your machine.

For made easy manage python dependences we preffer use Anaconda distribution. For this reason this manual are based on it.

Basically at this moment Spyder need this packages (as well your dependences) for run.

> * qtpy
* qtawesome 
* docutils 
* jinja2 
* sphinx 
* pyflakes 
* qtconsole 
* nbconvert 
* rope 
* jedi 
* psutil 
* pep8

We give you two ways for made a isolated enviroment for test and run Spyder.

For did't broke your python system in your machine (a lot of Thank's Anaconda).

1. conda create -n SpyderDev python=3 qtpy  qtawesome docutils jinja2 sphinx pyflakes qtconsole nbconvert rope jedi psutil pep8

### Update spec-file for SpyderDev enviroment
* source activate SpyderDev
* conda list --explicit >  SpyderDev_spec-file.txt
* conda env export > environment.yml

### Create Spyder-Dev enviroment for spec-file
* conda create --name SpyderDev --file SpyderDev_spec-file.txt


> Ref pages:
* http://conda.pydata.org/docs/using/envs.html#export-the-environment-file