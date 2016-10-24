# Hi Devs!!!

In order to develop and test Spyder, you will need some python packages on your machine.

For made easy manage python dependencies we prefer to use Anaconda distribution. For this reason this manual are based on it.

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

Isolated development environment to create anaconda is able to handle the requirements of your system python affected. (a lot of Thank's Anaconda).


## Install Anaconda distribution

First thing we will need for develop or test Spyder is have python and list of packages required for Spyder.

1. Download the installer from [here](https://www.continuum.io/downloads)
2. Optional: Verify data integrity with MD5 or SHA-256   More info
3. In your terminal window type one of the below and follow the instructions:

#### Python 3.X version (Reccommended for Spyder Development)

``` bash
bash Anaconda3-X.X.X-Linux-<arch>.sh 
```

## Create Spyder-Dev enviroment from spec-file.yml (Recommended)


#### Create the enviroment.
``` bash
conda env create -f ${Spyder_root_folder}/SpyderDev-Docs/SpyderDev_spec-file.yml
```

#### Activate de enviroment to work or test Spyder

``` bash
source activate SpyderDev
```

#### Develop and test Spyder!!!  :)

``` bash
python boostrap.py
```

## Create a enviroment directly on Anaconda

#### Create the enviroment with packages required.
``` bash
conda create -n SpyderDev python=3 qtpy  qtawesome docutils jinja2 sphinx pyflakes qtconsole nbconvert rope jedi psutil pep8
```

#### Activate de enviroment to work or test Spyder

``` bash
source activate SpyderDev
```

## Update spec-file for SpyderDev enviroment

As you sure want to be a Spyder developer you need keep this in mind, whenever possible.


> IMPORTANT:

> As developers come on **from anywhere, any time and any OS**. We need **guaranty!!** that it's possible test and run Spyder for any new developer.

> So if in some point you develop code that requires a new package, it's necessary you update the enviroment list of packages for another developers as well community of userxs. 


To enable another developers to create an exact copy of your environment, you will export the active environment file.

```bash 
source activate SpyderDev
conda env export > ${Spyder_root_folder}/SpyderDev-Docs/SpyderDev_spec-file.yml
```


> Ref pages:
* http://conda.pydata.org/docs/using/envs.html