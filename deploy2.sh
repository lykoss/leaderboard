#!/bin/bash

# this script is executed on the webserver

# there's a bunch of sleep commands to guard things that don't necessarily
# complete in realtime; should evaluate if they're actually necessary
# and if they are how small we can make them

##########
# set up correct version of python/pip
##########
echo "Initializing deployment"
export VIRTUAL_ENV_DISABLE_PROMPT=1
source /home/werewolf/virtualenv/leaderboard/3.10/bin/activate

SOURCEPATH=/home/werewolf/repositories/leaderboard
DESTPATH=/home/werewolf/leaderboard
BAKPATH=/home/werewolf/leaderboard.bak

##########
# make a backup
##########
echo "Creating backup"
rm -rf $BAKPATH
mv $DESTPATH $BAKPATH

##########
# ensure dependencies are up to date
##########
echo "Ensuring updated dependencies"
cd $SOURCEPATH
pip install --upgrade -r requirements.txt

##########
# copy files
##########
echo "Copying files"
mkdir $DESTPATH
mkdir $DESTPATH/tmp
cp -r . $DESTPATH

##########
# cleanup unnecessary files
##########
rm -rf $DESTPATH/.git
rm -rf $DESTPATH/.github
rm -f $DESTPATH/.gitignore
rm -f $DESTPATH/.cpanel.yml
rm -f $DESTPATH/deploy*

##########
# restart app
##########
echo "Restarting webapp"
touch $DESTPATH/tmp/restart.txt
sleep 5

##########
# test if app runs successfully
##########
SUCCESS=0
curl -f https://werewolf.chat/leaderboard > /dev/null
if [ $? -ne 0 ]; then
    SUCCESS=1
fi

sleep 5
if [ -s $DESTPATH/stderr.log ]; then
    SUCCESS=1
fi

##########
# restore backup if app didn't run successfully
##########
if [ $SUCCESS -eq 1 ]; then
    echo "Webapp failed, restoring backup. Below is what was found in the log:"
    cat $DESTPATH/stderr.log
    rm -rf $DESTPATH
    mv $BAKPATH $DESTPATH
    touch $DESTPATH/tmp/restart.txt
    sleep 5
    curl -f https://werewolf.chat/leaderboard > /dev/null
    echo "Backup restored"
fi

echo "Deployment complete"
exit $SUCCESS
