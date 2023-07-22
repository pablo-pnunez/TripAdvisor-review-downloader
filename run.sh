#!/bin/bash

MAXTSTS=4

declare -a CITIES=( "Warsaw" "Budapest" "Hamburg" "Vienna" "Bucharest" "New York City" "Rome" "Berlin" "London" "Porto", "Lisbon" )
declare -a CITIES=( "Gijon" "Madrid" "Barcelona" "Paris")
declare -a CITIES=( "Gijon" "Barcelona" )

 for CITY in "${CITIES[@]}" ;do
    echo "-$CITY"
   
    nohup /media/nas/pperez/miniconda3/envs/TripAdvisorDownload/bin/python -u  Main.py "$CITY" > "download_$CITY.log" &      

    # Si se alcanza el máximo de procesos simultaneos, esperar
    while [ $(jobs -r | wc -l) -eq $MAXTSTS ];
    do
      sleep 5
    done

done

# Esperar por los últimos
while [ $(jobs -r | wc -l) -gt 0 ];
do
  sleep 5
done