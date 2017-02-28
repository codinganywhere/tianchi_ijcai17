# -*- coding: utf-8 -*-
"""
Created on Sat Feb 25 15:20:03 2017

@author: LiuYangkai
"""
import os, logging
import pandas as pd
from datetime import datetime
from datetime import timedelta
def crossJoin(df1, df2):
    '''两个DataFrame的笛卡尔积'''
    df1['_temp_key'] = 1
    df2['_temp_key'] = 1
    df = df1.merge(df2, on='_temp_key')
    df.drop('_temp_key', axis='columns')
    return df
def getLabels(dat, mode='train'):
    '''获取真实数据'''
    dat = dat[(dat['stamp'] >= '2015-07-08') & 
              (dat['stamp'] <= '2016-10-31')]
    dat = dat.groupby(['sid', 'stamp']).size().reset_index()
    return dat
def extractAll(mode = 'train'):
    featurePath = os.path.join('../temp/', mode + '_features.csv')
    labelPath = os.path.join('../temp/', mode + '_labels.csv')

    if os.path.exists(featurePath) and\
       os.path.exists(labelPath):
        return (pd.read_csv(featurePath, header = None), 
                pd.read_csv(labelPath, header = None))

    #提取特征
    user_pay = pd.read_csv('../input/dataset/user_pay.txt', 
                           header = None, names = ['uid', 'sid', 'stamp'])
    labels = getLabels(user_pay)
    f1 = Last_week_sales(mode=mode)
    f1 = f1.extract(user_pay)
    features = f1
    #保存计算的features到outPath
    features.to_csv(featurePath, header=False, index=False, encoding='utf-8')
    labels.to_csv(labelPath, header=False, index=False, encoding='utf-8')
    return (features, labels)
#
class BaseFeature:
    def __init__(self, outDir = '../temp/', 
                 featureName = 'base', mode = 'train'):
        self.outFile = os.path.join(outDir, mode + '_' + featureName + '.csv')
        self.name = featureName
        self.data = None
        if os.path.exists(self.outFile):
            self.data = pd.read_csv(self.outFile, header = None)
            logging.info('从%s中载入特征%s.' (self.outFile, self.name))
    def extract(self, indata):
        return self.data
#
class Last_week_sales(BaseFeature):
    def __init__(self, mode = 'train'):
        BaseFeature.__init__(self, 
                             featureName = 'Last_week_sales',
                             mode = mode)
    def extract(self, indata):
        if self.data is not None:
            return self.data
        if isinstance(indata, str):
            indata = pd.read_csv(indata, header = None)
        #提取特征
        dat = indata
        dat['stamp'] = dat['stamp'].str[:10]
        dat = dat.groupby(['sid', 'stamp']).size().reset_index()
        #生成格式为sid, stamp的DataFrame；其中sid取值[1, 2000]，
        #stamp是[2015-07-08, 2016-10-31]。最后生成的DF是两者的笛卡尔积
        date_list = list(pd.date_range('2015-07-08', '2016-10-31').strftime('%Y-%m-%d'))
        date_list.remove('2015-12-12')
        sid_pf = pd.DataFrame({'sid':[str(k) for k in range(1, 2001)]})
        stamp_pf = pd.DataFrame({'stamp':date_list})
        days = crossJoin(sid_pf, stamp_pf)
        #
        dat.rename_axis({0:'sales'}, axis='columns', inplace=True)
        dat = dat.sort_values(['sid', 'stamp'])
        dat = dat.astype({'sid':str, 'stamp':str, 'sales':int})
        applyFunc = lambda k:\
            lambda s:(datetime.strptime(s, '%Y-%m-%d') + 
                      timedelta(days=k+1)).\
                      strftime('%Y-%m-%d') \
                      if '2015-12-05' <= s and s <= '2015-12-12'\
                      else\
                      (datetime.strptime(s, '%Y-%m-%d') + 
                      timedelta(days=k)).strftime('%Y-%m-%d')
        
        for k in range(1, 8):
            day = dat[(dat['stamp'] >= ('2015-07-0%d' % k)) & 
                      (dat['stamp'] <= ('2016-10-%d' % (23+k)))]
            timeShift = day.stamp.apply(applyFunc(8-k))
            day = day.drop('stamp', axis='columns')
            day = day.rename_axis({'sales':'day%d'%k}, axis='columns')
            day.insert(1, 'stamp', timeShift)
            days = days.merge(day, how='left', on=['sid', 'stamp'])
            days['day%d'%k].fillna(0, inplace=True)
        days.to_csv(self.outFile, header=False, index=False, encoding='utf-8', 
                          float_format='%0.0f')
        return days