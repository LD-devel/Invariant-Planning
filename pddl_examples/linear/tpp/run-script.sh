
dir=$1

for file in $dir*
do
  python script.py "$file"
done
