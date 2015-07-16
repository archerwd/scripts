#!/usr/bin/env python
# -*- coding: utf8 -*-
'''
Created on Jul 14, 2014

@author: wudong

解析blktrace收集的trace，使用blktrace然后用blkparse转换一遍后方便解析
blktrace -d /dev/vdb -a complete -o - | blkparse -i - -o vdb.bin
这样出来的记录类似，格式说明参考blktrace User Guide
254,16   0        2     0.021174925     0  C   R 78156240 + 576 [0]
254,16   0        3     0.054676020     0  C  WS 43325520 + 216 [0]

其中的"78156240 + 576"的单位是扇区(512Bytes)
最后需要解析成<offset>,<size>,<rw>
'''
import os
import sys
from optparse import OptionParser, OptionValueError

def parse_data(filename, saveFile):
    fd = open(filename, "r")
    outfd = open(saveFile, "w")
    totalReadSize = 0
    totalWriteSize = 0
    try:
        lines = fd.readlines()
        for line in lines:
            cells = line.split()
            if len(cells) != 11:
                continue
            offset = int(cells[-4])
            size = int(cells[-2])
            rw = cells[-5]
            if rw == "W" or rw == "WS":
                rw = "w"
                totalWriteSize += size * 512
            elif rw == "R" or rw == "RS":
                rw = "r"
                totalReadSize += size * 512
            record = "%d,%d,%s\n" % (offset*512, size*512, rw)
            outfd.write(record)
    finally:
        fd.close()
        outfd.close()
    print "totalReadSize: %d" % totalReadSize
    print "totalWriteSize: %d" % totalWriteSize
    

def iotrace_by_block(filename, saveFile, blockSize):
    """
    按照指定块大小对io trace文件进行统计，统计出每个block的访问次数
    """
    fd = open(filename, "r")
    countDict = {}
    try:
        lines = fd.readlines()
        for line in lines:
            line = line.split("\n")[0]
            cells = line.split(",")
            offset = int(cells[0])
            size = int(cells[1])
            rw = cells[2]
            blockid = offset / blockSize
            if blockid in countDict:
                if rw == "r":
                    countDict[blockid][0] += 1
                else:
                    countDict[blockid][1] += 1
                countDict[blockid][2] += 1
            else:
                countDict[blockid] = [0, 0, 0]
                if rw == "r":
                    countDict[blockid][0] += 1
                else:
                    countDict[blockid][1] += 1
                countDict[blockid][2] += 1
    finally:
        fd.close()
    
    blkCountList = sorted(countDict.items(), lambda x,y: cmp(x[0], y[0]))
    # 类似 [(536, [0, 3, 3]), (1760, [0, 7, 7]), (1968, [0, 5, 5]), (7560, [0, 3, 3])]
    outfd = open(saveFile, "w")
    try:
        for blkCount in blkCountList:
            blockid = blkCount[0]
            count = blkCount[1]
            #line = "%d %d %d %d\n" % (blockid, count[0], count[1], count[2])
            line = "%d %d %d\n" % (blockid, count[0], count[1])
            outfd.write(line)
    finally:
        outfd.close()

def gen_jpg(file, title, blkStr):
    outFile = '%s.jpg' % title
    cmd = '''
    gnuplot <<EOF
    
    set grid
    set size 1,1
    set term jpeg
    set output '%s'
    set title "%s"
    set ylabel "count"
    set xlabel "blockId(block size: %s)"
    set style data points
    plot ''' % (outFile, title, blkStr) 
 
    #set style data linespoints
    cmd = cmd +'"%s" using %d:%d title "read count"' % (file, 1, 2)
    cmd = cmd +',"%s" using %d:%d title "write count"' % (file, 1, 3)
    #cmd = cmd +',"%s" using %d:%d  title "total count"' % (file, 1, 4)
    cmd = cmd +'\nEOF\n'
    print cmd
    os.system(cmd)
    
def main():

    parser = OptionParser()

    parser.add_option("-f", "--filename", action="store", dest="filename", default="",
                      help="Specifies source data file")
    
    parser.add_option("-b", "--blocksize", action="store", dest="blocksize", default="",
                      help="Specifies block size(Bytes,K,M)")
    
    parser.add_option("-o", "--outFile", action="store", dest="outFile", default="",
                      help="Specifies output file")
    
    (options, args) = parser.parse_args()
    if len(options.filename) > 0:
        filename = options.filename
    else:
        parser.print_help()
        exit(1)
    
    if len(options.blocksize) > 0:
        blkstr = options.blocksize
        if blkstr[-1] == "K":
            blockSize = int(blkstr[0:-1]) * 1024
        elif blkstr[-1] == "M":
            blockSize = int(blkstr[0:-1]) * 1024 * 1024
        else:
            blockSize = int(blkstr)
    else:
        parser.print_help()
        exit(1)
        
    if len(options.outFile) > 0:
        outFile = options.outFile
    else:
        parser.print_help()
        exit(1)
        
    parse_data(filename, outFile)
    newFile = "%s.%s" % (outFile, blkstr)
    iotrace_by_block(outFile, newFile, blockSize)
    title = "io_count_statistics.%s" % newFile
    gen_jpg(newFile, title, blkstr)
    
if __name__ == '__main__':
    main()
