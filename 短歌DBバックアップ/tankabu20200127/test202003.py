#!/usr/bin/env python3
import re
import urllib.request
import urllib.parse
import json
from flask import Flask, render_template,request,jsonify
from flask_paginate import Pagination, get_page_parameter
from gensim.models import word2vec

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False 

#トップページ
@app.route('/')
def hello():
    result=[]
    hensuu=""
    hit_author={}
    pagination=""
    y_labels_list=[]
    bar_labels=[]
    graph_data_list=[]
    backgroundColor_list=[]
    html =render_template("index.html",hit_author=hit_author,pagination=pagination,y_labels_list=y_labels_list,bar_labels=bar_labels,graph_data_list=graph_data_list,backgroundColor_list=backgroundColor_list)
    return html
 
@app.route('/test', methods=['GET', 'POST'])
def test():
    if request.method == 'GET':
        res = request.args.get('get_value')
    elif request.method == 'POST':
        res = request.args.get['post_value']    
    return res

#検索語、歌人名がand検索された際の処理
@app.route('/output/')
def hello_1():
    hit_poet_list=[]
    encorded_word_list=[]
    encorded_kajin_list=[]
    year_count_dic={}
    author_dic= {}
    graph_data_list=[]
    y_labels_list=[]
    bar_labels=[]
    hensuu=""
    year_count_dic1={}

    per_page_org = 20 #検索結果の表示数
    keyword = request.args.get('s_keyword', '')#キーワード
    kajin_list=request.args.getlist('s_author')#歌人
    search_method=request.args.get('search_method', '')#and 検索とor検索の選択
    hit_author=request.args.get('hit_author', '')#絞り込み検索の歌人
    hit_title=request.args.get('hit_title',' ')#絞り込み検索のタイトル
    graph_num=request.args.get('m_num', '')#分析年代間隔
    size=request.args.get('size', '')#w2vベクトル空間サイズ
    window=request.args.get('window', '')#w2v文脈幅
    min_count=request.args.get('min_count', '')#w2v単語の最低出現回数
    page = request.args.get(get_page_parameter(), type=int, default=1)
    startrow = (page - 1) * per_page_org

   #Apatch sorlに問い合わせるURLを作成
    base_url = 'http://127.0.0.1:8983/solr/mycore/select?q='
    query_poet_fld = 'poet%3A'#検索対象フィールドがpoet
    query_author_fld='%20OR%20'+'author%3A'
    #複数キーワードとADN検索、OR検索の処理
    wordlist=keyword.split()

    #歌人とタイトルでしぼり込み検索する場合のApachesorlへの問い合わせURL
    if hit_author !="":
        if hit_title !="":
            query_title="%20AND%20title%3A"+urllib.parse.quote(hit_title)
            query_author2="%20AND%20author%3A"+urllib.parse.quote(hit_author)
            if len(wordlist) !=1:  #検索キーワードが複数ある場合の処理
                if search_method=="and":
                    for word in wordlist:
                        mojimoji='\"'+urllib.parse.quote(word)+'\"'
                        encorded_word_list.append(mojimoji)
                    #hensuu=encorded_word_list
                    moji="%20AND%20"+query_poet_fld
                    query_key=moji.join(encorded_word_list)
                    query_key_poet=query_poet_fld+query_key
                    hensuu=query_key_poet
                        
                if search_method=="or":
                    for word in wordlist:
                        encorded_word_list.append(urllib.parse.quote(word))
                    moji="%20OR%20"+query_poet_fld
                    query_key=moji.join(encorded_word_list)
                    query_key_poet=query_poet_fld+query_key
            else:#検索キーワードが一つだけの場合
                for word in wordlist:
                    encorded_word=urllib.parse.quote(word)
                    query_key_poet=query_poet_fld+encorded_word
        
        #作者を検索するULR
        query_url1 = base_url +query_key_poet+query_author2+query_title #Apatch sorlに問い合わせるURL


    #絞り込み以前の検索
    else:
        if len(wordlist) !=1:  #検索キーワードが複数ある場合の処理
            if search_method=="and":
                for word in wordlist:
                    encorded_word_list.append(urllib.parse.quote(word))
                moji="%20AND%20"+query_poet_fld
                query_key=moji.join(encorded_word_list)
                query_key_poet=query_poet_fld+query_key
                    
            if search_method=="or":
                for word in wordlist:
                    encorded_word_list.append(urllib.parse.quote(word))
                moji="%20OR%20"+query_poet_fld
                query_key=moji.join(encorded_word_list)
                query_key_poet=query_poet_fld+query_key
        else:#検索キーワードが一つだけの場合
            for word in wordlist:
                encorded_word=urllib.parse.quote(keyword)
                query_key_poet=query_poet_fld+encorded_word
        
        #作者を検索するULR
        #「すべて」が選択された時
        if "すべて" in kajin_list:
            query_url1 = base_url +query_key_poet #Apatch sorlに問い合わせるURL
        #複数の歌人が選択された時
        else:
            for kajin in kajin_list:
                encorded_kajin_list.append(urllib.parse.quote(kajin))
            query_author=query_author_fld.join(encorded_kajin_list)
            query_url1 = base_url +query_key_poet+"%20AND%20"+"(author:"+query_author+")"

    #キーワード、作者の条件が入ったURLにファセットとページネーションの要素を入れる

    sorl_url_1=query_url1+'&facet.pivot=author_st,title_st&facet=on&fl=poet,author,title,id,year,group&rows=20&facet.sort=count&rows='+str(per_page_org)+'&start='+str(startrow)
    #グラフのヒット数集計用の検索結果を返すURL
    sorl_url_2=query_url1+'&rows=1000'
   
     #問い合わせる
    result_1 = urllib.request.urlopen(sorl_url_1) #戻ってきた検索結果を変数resultに入れる
    result_2 = urllib.request.urlopen(sorl_url_2)
    array_body_1 = json.loads(result_1.read().decode('utf-8'))#返送されてきたjsonをpythonの辞書に変換して受け取る
    array_body_2 = json.loads(result_2.read().decode('utf-8'))

    for edoc in array_body_1['response']['docs']:
        obj_id = edoc['id']
        poet=edoc['poet']
        title=edoc['title'][0]
        author=edoc['author'][0]
        #単語をハイライト
        for word in wordlist:
                hilight_poet=re.sub(word,"<span class=hitword>"+word+"</span>",poet)#検索結果のハイライト表示
                hit_poet_list.append(hilight_poet+":"+author+":"+title)

    #ヒット件数を変数hit_poet_numに入れる
    hit_poet_num=array_body_1['response']["numFound"]
    #ページネーションの機能
    pagination = Pagination(page=page, total=hit_poet_num,  per_page=per_page_org, css_framework='bootstrap4')


    #年代ごとのヒット件数をグラフ表示
    #{{キーワード:{"n_year":年代,"hit_num":ヒット数}}という辞書を作成
    for edoc in array_body_2['response']['docs']:
        year=edoc['year'][0]
        poet=edoc['poet']
        #y_labels.append(poet)
        y_year=year // int(float(graph_num))
        n_year=y_year* int(float(graph_num))
        
        for word in wordlist:
            if word in poet:
                if word not in year_count_dic.keys():
                    year_count_dic[word]={}
                else:
                    pass
                if n_year not in year_count_dic[word].keys():
                    year_count_dic[word][n_year]=1
                else:
                    year_count_dic[word][n_year]+=1
            else:
                pass
        for k1,v1 in year_count_dic.items():
            year_count_dic1[k1]=[]
            for k2,v2 in v1.items():
                dic2={}
                dic2["n_year"]=str(k2)
                dic2["hit_num"]=v2
                year_count_dic1[k1].append(dic2)
    year_count_dic2={}
    for k1,v1 in year_count_dic1.items():
        v2 = sorted(v1, key=lambda x: x["n_year"])
        year_count_dic2[k1]=v2
    graph_data=[]
    graph_data_num=1
    for k1 ,v1 in year_count_dic2.items():
        bar_labels.append(k1)
        name1="y_labels"+str(graph_data_num)
        name2="data"+str(graph_data_num)
        y_labels_list=[]
        name3=v1
        for items in v1:
                if items["n_year"] not in y_labels_list:
                    y_labels_list.append(str(items["n_year"]))
                
    graph_data_num+=1
  
    hity_hitn_list=[]
    list7=[]
    for k1 ,v1 in year_count_dic2.items():
        list5=[]
        for i in y_labels_list:
            count = 0
            for items in v1:
                if  i in items["n_year"]:
                    count = items["hit_num"]
            list5.append(i+':'+str(count))
        hity_hitn_list.append(list5)
    for i1 in hity_hitn_list:
        list7=[]
        for i2 in i1:
            list6=i2.split(":")
            list7.append(list6[1])
        graph_data_list.append(list7)
    backgroundColor_list=['rgba(255, 99, 132, 0.2)','rgba(54,164,235,0.5)','rgba(255, 205, 86, 0.2)']
    #y_labels_list:y軸のラベル(年代)
    #graph_data_list:年代ごとのヒット数
    #bar_labels:キーワードのラベル


    #しぼりこみ検索
    facet_pivot_dic = array_body_1['facet_counts']['facet_pivot']["author_st,title_st"]
    
    hit_author_list=[]
    for author_st in facet_pivot_dic:
        hit_author=author_st["value"]
        hit_author_list.append(hit_author)
        hit_author_num=author_st["count"]
        hit_author_text=hit_author+"("+str(hit_author_num)+")"
        if hit_author_text not in author_dic.keys():
            author_dic[hit_author_text]={}
        if 'pivot' in author_st:
            for title_st in author_st['pivot']:
                hit_title = title_st['value']
                hit_title_num = title_st['count']
                hit_title_text=hit_title+"("+str(hit_title_num)+")"
                #URLの作成
                facet_url="?s_keyword="+keyword+"&search_method="+search_method+"&m_num="+graph_num+"&hit_author="+hit_author+"&hit_title="+hit_title
                
                author_dic[hit_author_text][facet_url]=hit_title_text
    hit_author=author_dic
    result=hit_poet_list
    
    html =render_template("index.html",hensuu=hensuu,navigation=result,hit_poet_num=hit_poet_num,hit_author=hit_author,pagination=pagination,keyword=keyword,y_labels_list=y_labels_list,graph_data_list=graph_data_list,
    bar_labels=bar_labels,backgroundColor_list=backgroundColor_list)
    return html

@app.route('/get_w2vec/')#ajaxで生成されたURLからw2vのパラメータを受け取る
def get_w2vec():
    keyword_list=[]
    get_size = request.args.get('size', '')
    get_min_count = request.args.get('min_count', '')
    get_window = request.args.get('window', '')
    keyword = request.args.get('s_keyword', '')
    wordlist=keyword.split()
    w2v_dict={"size":get_size,"min_count":get_min_count,"window":get_window,"keyword":keyword}
#モデルファイルの選択
    file_name="model_s"+get_size+"_minc"+get_min_count+"_win"+get_window+".model"
#モデルのよみこみ
    model = word2vec.Word2Vec.load(file_name)
#w2vの結果をJson形式で返還
    for word in wordlist:
        similar_words = model.wv.most_similar(positive=[word], topn=15)
        word2Vec={}
        word2Vec["keyword"]=word
        word2Vec["most_similar_data"]=[]
        for w2vdata_l in similar_words:
                w2v_list=list(zip(w2vdata_l[0::2],w2vdata_l[1::2]))
                for i in w2v_list:
                    w2v_data={}
                    w2v_data["similar_word"]=i[0]
                    w2v_data["similarity"]=i[1]
                    word2Vec["most_similar_data"].append(w2v_data)
        keyword_list.append(word2Vec)
    return jsonify(keyword_list)

if __name__ == "__main__":
    #デバッグ
    app.run(debug=True)