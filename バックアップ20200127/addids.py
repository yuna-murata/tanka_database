#!/usr/bin/env python3

from bs4 import BeautifulSoup

n=1
with open('shakko-re_yomi.xml' , encoding='utf-8') as f:
    all_data = BeautifulSoup(f, 'xml')
    sentences = all_data.find_all(["l"])
    for sentence in sentences:
     sn = str(n).zfill(4)
     sn = 'M'+"01"+"02"+sn+'00'
     sentence["xml:id"] = sn
     n = n + 1
    print (all_data)
