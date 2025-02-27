#!/bin/bash

mapfile -t nodes_array < <(kubectl get nodes --no-headers -o custom-columns=":metadata.name")

for n in "${nodes_array[@]}"; do
    mapfile -t nodes_array < <(kubectl get node ipp1-2183 --show-labels --no-headers | tr ',' '\n')
    #echo "${nodes_array[@]}"
    num_labels=${#nodes_array[@]}
    echo "Number of labels on node 'n': $num_labels"
    for l in "${nodes_array[@]}"; do
        if [[ "$l" == *"nvidia"* ]]; then
            substring="${l%%=*}"
            kubectl label nodes "$n" "${substring}-"
            echo "$l"
            #echo -e "\n"
        fi
    done
done
