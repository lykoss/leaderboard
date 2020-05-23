import json
import requests
import sys
import logging
import pprint
import time
import os

# this script is executed in a github actions container

DEBUG_MODE = int(os.environ["DEBUG"])

def run():
    gh_owner = os.environ["GITHUB_OWNER"]
    gh_owner_repo = os.environ["GITHUB_REPO"]
    gh_repo = gh_owner_repo[len(gh_owner)+1:]

    cp_repo = os.environ["CPANEL_REPO_PATTERN"].format(owner=gh_owner, repo=gh_repo)
    gh_deploy = "repos/{}/deployments".format(gh_owner_repo)

    # add some logging about web requests that we make
    if DEBUG_MODE:
        logging.basicConfig(level=logging.DEBUG)

    # make a new deployment in github
    res = github_api("POST", gh_deploy, {
        "ref": os.environ["GITHUB_SHA"],
        "task": "deploy",
        "auto_merge": False,
        "environment": os.environ["CPANEL_ENV"]
    })

    gh_deploy_status = "{}/{}/statuses".format(gh_deploy, res["id"])
    gh_status_url = "https://github.com/{}/actions/{}".format(gh_owner_repo, os.environ["GITHUB_RUN_ID"])
    res = github_api("POST", gh_deploy_status, {
        "state": "pending",
        "target_url": gh_status_url,
        "description": "Initializing deployment"
    })

    # Updates the repo to the latest master revision
    res = cpanel_api("VersionControl", "update", {
        "repository_root": repo,
        "branch": "master"
    })
    if not res["status"]:
        raise RuntimeError("API call was unsuccessful, aborting!")

    # check if we can execute a deploy
    # if this fails, it's because the repo on the webserver has changes
    # or is missing a .cpanel.yml file with deployment steps
    if not res["data"]["deployable"]:
        raise RuntimeError("Repository is not deployable, aborting!")

    # create a deployment
    res = cpanel_api("VersionControlDeployment", "create", {
        "repository_root": repo
    })
    if not res["status"]:
        raise RuntimeError("API call was unsuccessful, aborting!")
    cp_deploy_id = res["data"]["deploy_id"]

    # mark deployment as queued
    gh_deploy_status = "{}/{}/statuses".format(gh_deploy, res["id"])
    res = github_api("POST", gh_deploy_status, {
        "state": "queued",
        "target_url": gh_status_url,
        "description": "Deployment {} queued at {} (task {})".format(res["data"]["deploy_id"],
                                                                     res["data"]["timestamps"]["queued"],
                                                                     res["data"]["task_id"])
    })

    # fetch deployment status (note: uses a custom API module since built-in
    # one doesn't let us filter on a specific deployment id)
    # Custom API module source code is available at:
    # https://gist.github.com/skizzerz/85a0a2d4a6176ffa67004cd22c507799
    cur_state = "queued"
    success = False
    i = 0
    while True:
        i += 1
        # if the deployment is taking forever, give up on checking status
        if i > 60:
            res = github_api("POST", gh_deploy_status, {
                "state": "error",
                "target_url": gh_status_url,
                "description": "No deployment response after 5 minutes, aborting action"
            })
            break
        print("Sleeping for 5 seconds then checking status")
        time.sleep(5)
        res = cpanel_api("VCDeployStatus", "retrieve", query={
            "deploy_id": cp_deploy_id
        })
        if not res["status"]:
            raise RuntimeError("API call was unsuccessful, aborting!")
        if res["data"]["timestamps"].get("succeeded", None):
            res = github_api("POST", gh_deploy_status, {
                "state": "success",
                "auto_inactive": True,
                "target_url": gh_status_url,
                "description": "Deployment {} succeeded at {} (task {})".format(res["data"]["deploy_id"],
                                                                                res["data"]["timestamps"]["succeeded"],
                                                                                res["data"]["task_id"])
            })
            success = True
            break
        if res["data"]["timestamps"].get("failed", None):
            res = github_api("POST", gh_deploy_status, {
                "state": "failure",
                "target_url": gh_status_url,
                "description": "Deployment {} FAILED at {} (task {})".format(res["data"]["deploy_id"],
                                                                             res["data"]["timestamps"]["failed"],
                                                                             res["data"]["task_id"])
            })
            break
        if res["data"]["timestamps"].get("canceled", None):
            res = github_api("POST", gh_deploy_status, {
                "state": "failure",
                "target_url": gh_status_url,
                "description": "Deployment {} CANCELED at {} (task {})".format(res["data"]["deploy_id"],
                                                                               res["data"]["timestamps"]["canceled"],
                                                                               res["data"]["task_id"])
            })
            break
        if cur_state == "queued" and res["data"]["timestamps"].get("active", None):
            res = github_api("POST", gh_deploy_status, {
                "state": "in_progress",
                "target_url": gh_status_url,
                "description": "Deployment {} began running at {} (task {})".format(res["data"]["deploy_id"],
                                                                                    res["data"]["timestamps"]["active"],
                                                                                    res["data"]["task_id"])
            })
        else:
            print("No new deployment status updates")

    return success

def cpanel_api(module, endpoint, body=None, query=None):
    headers = {
        "Authorization": "cpanel {}:{}".format(os.environ["CPANEL_API_USER"], os.environ["CPANEL_TOKEN"])
    }

    url = "{}/execute/{}/{}".format(os.environ["CPANEL_API_URL"], module, endpoint)
    method = "POST" if body else "GET"
    print(method, url)
    r = requests.request(method, url, headers=headers, params=query, data=body)
    r.raise_for_status()
    data = r.json()
    if DEBUG_MODE:
        pprint.pp(data)
    return data

def github_api(method, endpoint, body=None):
    headers = {
        "Authorization": "Bearer {}".format(os.environ["GITHUB_TOKEN"]),
        # opt into preview letting us set additional deployment status types
        # remove this line once it hits stable API
        "Accept": "application/vnd.github.flash-preview+json, aplication/vnd.github.ant-man-preview+json"
    }

    url = "https://api.github.com/{}".format(endpoint)
    print(method, url)
    r = requests.request(method, url, headers=headers, json=body)
    r.raise_for_status()
    data = r.json()
    if DEBUG_MODE:
        pprint.pp(data)
    return data

if __name__ == "__main__":
    if not run():
        sys.exit(1)
