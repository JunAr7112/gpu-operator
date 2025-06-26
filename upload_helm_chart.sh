#!/bin/bash

push_helm_chart() {
    local REL_TAG=$1
    echo "Updating helm chart for ${REL_TAG}"

    git fetch --tags
    git checkout ${REL_TAG}
    helm package --version ${REL_TAG} --app-version ${REL_TAG} deployments/gpu-operator
    git checkout gh-pages
    git checkout -b helm-release-${REL_TAG}

    rm -rf new-chart && mkdir new-chart
    mv gpu-operator-${REL_TAG}.tgz new-chart/
    helm repo index new-chart --merge stable/index.yaml --url https://nvidia.github.io/gpu-operator/stable
    mv new-chart/*.tgz new-chart/index.yaml stable

    git add stable/
    git commit -s -m "helm release for ${REL_TAG}" --signoff
    git push origin -u helm-release-${REL_TAG}
    rm gpu-operator-${REL_TAG}.tgz
}

update_nvstaging() {
    local REL_TAG=$1
    echo "Updating nvstaging for ${REL_TAG}"

    helm plugin install https://github.com/chartmuseum/helm-push
    git fetch --tags
    git checkout ${REL_TAG}
    helm package --version ${REL_TAG} --app-version ${REL_TAG} deployments/gpu-operator
    helm repo add ea-cnt-nv_only https://helm.ngc.nvidia.com/ea-cnt/nv_only --username='$oauthtoken' --password=${API_TOKEN}
    helm cm-push --force gpu-operator-${REL_TAG}.tgz ea-cnt-nv_only
    rm gpu-operator-${REL_TAG}.tgz
}

curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/master/scripts/get-helm-3 && chmod 700 get_helm.sh && ./get_helm.sh && rm get_helm.sh
push_helm_chart $1
update_nvstaging $1
