#! /bin/bash
# -*- coding: utf-8 -*-

# package info
ppa="ppa:colin-duquesnoy/stable"
name="qdarkstyle"
version="2.0"

# read pgp key from gpg_key file
gpg_key=`cat gpg_key`

# generate debian source package and .orig.tar.gz
python3 setup.py --command-packages=stdeb.command sdist_dsc

date=`date -R`

# clean pyc files
find . -name "*.pyc" -exec rm -rf {} \;


for suite in 'trusty' 'utopic' 'vivid'
do
    # sign our package and prepare it for ppa upload
    pushd deb_dist
    pushd ${name}-${version}
    
    # update changelog to include ubuntu release
    changelog="${name} (${version}-1ppa1~${suite}1) ${suite}; urgency=low
  * Initial release
 -- Colin Duquesnoy <colin.duquesnoy@gmail.com>  ${date}
"
    echo "$changelog" > debian/changelog
    cat debian/changelog

    debuild -S -sa -k${gpg_key}
    popd

    # upload to ppa
    dput ${ppa} *.changes      
    rm -rf *.dsc *.changes

    popd
done

# cleanup
rm -rf *.tar.gz deb_dist/ dist/
