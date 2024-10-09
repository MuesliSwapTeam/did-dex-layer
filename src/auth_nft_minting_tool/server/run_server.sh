restart=""
while true; do
    timeout 180 node server $restart
    restart="restart"
done &