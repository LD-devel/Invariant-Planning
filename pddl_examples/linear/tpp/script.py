import sys
from tempfile import mkstemp
from shutil import move
from os import fdopen, remove
import re

def replaceAt(filename):
    with open(filename,'r') as fo:
        data = fo.read()
        data = data.replace('(at ', '(located ')
    with open(filename,'w') as fo:
        fo.write(data)
    return

def replace(file_path):
    #Create temp file
    fh, abs_path = mkstemp()
    with fdopen(fh,'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                new_file.write(line)
                if 'on-sale' in line:
                    l = line.split(' ')
                    val = int(re.findall(r'\d+', l[-1])[0])
                    if val == 0:
                        price_line ='	(= (price {} {}) 0)\n'.format(l[-3],l[-2].strip(')'))
                        new_file.write(price_line)
                        
    #Remove original file
    remove(file_path)
    #Move new file
    move(abs_path, file_path)

def removeMetric(file_path):
    #Create temp file
    fh, abs_path = mkstemp()
    with fdopen(fh,'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                if ':metric' not in line:
                    new_file.write(line)         
    #Remove original file
    remove(file_path)
    #Move new file
    move(abs_path, file_path)

    

def main():
    file_path = sys.argv[1]
##    replaceAt(file_path)
##    replace(file_path)
    removeMetric(file_path)

if __name__ == '__main__':
    main()
