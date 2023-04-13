#!/bin/bash

MAXTSTS=4

declare -a CITIES=( "Gijon" "Barcelona" "Warsaw" "Budapest" "Hamburg" "Vienna" "Bucharest" "New York City" "Paris" "Rome" "Madrid" "Berlin" "London" )
declare -a CITIES=( "Barcelona" "Paris")

 for CITY in "${CITIES[@]}" ;do
    echo "-$CITY"
   
    nohup /media/nas/pperez/miniconda3/envs/TripAdvisorDownload/bin/python -u  Main.py "$CITY" > "download_$CITY.log" &      

    # Si se alcanza el máximo de procesos simultaneos, esperar
    while [ $(jobs -r | wc -l) -eq $MAXTSTS ];
    do
    sleep 5
    done

    done
done

# Esperar por los últimos
while [ $(jobs -r | wc -l) -gt 0 ];
do
  sleep 5
done