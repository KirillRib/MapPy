import geojson
from PIL import Image, ImageDraw
from pyproj import Proj, transform
import numpy as np
from simplification.cutil import simplify_coords, simplify_coords_vw, simplify_coords_vwp
import aggdraw
import copy
import timeit
import yaml
import pickle
import os.path


#Генератор изображений
DefaultStyle = {'color': 'red', 'width': 2}
sizeOfShortCoordinates = 0.001

def LoadData(fileName):
    with open(fileName, encoding='utf-8') as f:
        gj = geojson.load(f)
        
        for feature in gj['features']:
            
            minP = [999.0, 999.0]
            maxP = [0.0, 0.0]
            centerP = [0.0, 0.0]
            pointsNumber = 0.0
            
            
            for a in feature['geometry']['coordinates']:
                for b in a:
                    for c in b:
                        c = ToConvertCoordinate(c)
                        
                        #Поиск минимальных и максимальных координат объекта
                        if c[0] < minP[0]:
                            minP[0] = c[0]
                        elif c[0] > maxP[0]:
                            maxP[0] = c[0]
                        if c[1] < minP[1]:
                            minP[1] = c[1]
                        elif c[1] > maxP[1]:
                            maxP[1] = c[1]
                        
                        #Поиск цента масс
                        centerP[0] += c[0]
                        centerP[1] += c[1]
                        pointsNumber += 1
            
            #Производит предварительное отсечение лишних вершин
            coordinates_short = []
            for a in feature['geometry']['coordinates']:
                a_short = []
                for b in a:
                    a_short.append(simplify_coords(b, sizeOfShortCoordinates))
                coordinates_short.append(a_short)
            feature['geometry']['coordinates_short'] = coordinates_short   
                    
            
            centerP[0] /= pointsNumber
            centerP[1] /= pointsNumber
            
            feature['properties']['minP'] = minP
            feature['properties']['maxP'] = maxP
            feature['properties']['centerP'] = centerP
            feature['properties']['w'] = maxP[0] - minP[0]
            feature['properties']['h'] = maxP[1] - minP[1]
            feature['properties']['density'] = pointsNumber / (maxP[0] - minP[0] + maxP[1] - minP[1]) / 2
        
        return gj['features']

def LoadStyles(fileName="C:\\Users\\79105\\Documents\\GitHub\\MapPy\\styles.yaml", encoding='utf-8'):
    with open(fileName, 'r') as stream:
        try:
            styles = yaml.load(stream)
            if styles.get('rules')==None:
                prib=print('Файл стилей должен содержать rules')
                return None
            elif styles.get('exceptions')==None:
                prib=print('Файл стилей должен содержать exceptions')
                return None
            return styles
        except yaml.YAMLError as exc:
            print(exc)

def GetLevelStyle(styles, admin_level):
    levelStyle = copy.copy(DefaultStyle)
    
    if styles['rules'].get(admin_level) != None:
        levelStyle = styles['rules'][admin_level]
    
    if levelStyle.get('color')==None:
        levelStyle['color'] = DefaultStyle['color']
    if levelStyle.get('width')==None:
        levelStyle['width'] = DefaultStyle['width']
    return levelStyle

def GetCurrentStyle(styles, levelStyle, feature):
    currentStyle = copy.copy(levelStyle)
    
    exception = styles['exceptions'].get(feature['properties']['name'])
    
    if exception != None:
        if exception.get('color')!=None:
            currentStyle['color'] = exception['color']
        if exception.get('width')!=None:
            currentStyle['width'] = exception['width']
    return currentStyle

def ToConvertCoordinate(c):
    if c[0]<0:
        c[0]=c[0]+360
    c[0]-=30

    c[0],c[1] = transform(Proj(init='epsg:4326'), Proj(init='epsg:3857'), c[0], c[1])
    c[0]=90+c[0]/200000+15
    c[1]=90-c[1]/200000
    
    return c



#Переводит координаты в формат для отрисовки
def ToNormalizeCoordinates(p, p0, size):
    x1 = (p[0]-p0[0]) * size
    y1 = (p[1]-p0[1]) * size
    return (x1, y1)

def ToCheckPointVisibility(p, p0, p1):
    if p[0] > p0[0] and p[1] > p0[1] and p[0] < p1[0] and p[1] < p1[1]:
        return True
    else:
        return False
def ToCheckPolygonVisibility(minP, maxP, p0, p1):
    if maxP[0] < p0[0] or maxP[1] < p0[1] or minP[0] > p1[0] or minP[1] > p1[1]:
        return False
    else:
        return True
    
def ToDrawPolygon(draw, coordinates, size, p0, p1, colour="red", width=1):
    previousP = -1
    norm_P0 = ToNormalizeCoordinates(copy.copy(p0), p0, size)
    norm_P1 = ToNormalizeCoordinates(copy.copy(p1), p0, size)
    points=[]
    
    for p in coordinates:
        points.append(ToNormalizeCoordinates(p, p0, size))
        continue
        #Не используемый код, предназначенный для рисования линиями
        if previousP == -1:
            previousP = ToNormalizeCoordinates(p, p0, size)
        else:
            currentP = ToNormalizeCoordinates(p, p0, size)
            
            if ToCheckPointVisibility(previousP, norm_P0, norm_P1) or ToCheckPointVisibility(currentP, p0, p1):
                draw.line((previousP[0], previousP[1], currentP[0], currentP[1]), fill=colour, width=int(width*size/100))
            previousP = currentP
        #
    draw.polygon(points,outline = colour)


def ToDrawPicture(x, y, z, P0, P1, pictureSize, activeLevelDictionary, styles):
    p0 = [0, 0]
    p1 = [0, 0]
    
    p0[0] = P0[0] + (P1[0] - P0[0]) * x / 2**z
    p0[1] = P0[1] + (P1[1] - P0[1]) * y / 2**z
    
    p1[0] = P0[0] + (P1[0] - P0[0]) * (x+1) / 2**z
    p1[1] = P0[1] + (P1[1] - P0[1]) * (y+1) / 2**z
    
    W = pictureSize
    H = pictureSize
    
    size = W / (p1[0] - p0[0])
    
    image = Image.new("RGBA", (int(W),int(H)), (250,250,255,255))
    draw = ImageDraw.Draw(image)
    
    for i in reversed(range(len(data))):
        dataLevel = data[i]
        if activeLevelDictionary.get(i)!=None and activeLevelDictionary[i]:
            currentStyle = GetLevelStyle(styles, i)
            
            for feature in dataLevel:
                
                if not ToCheckPolygonVisibility(feature['properties']['minP'], feature['properties']['maxP'], p0, p1):
                    continue
                
                coordinates = feature['geometry']['coordinates']
                if 1 / size / 10 > sizeOfShortCoordinates:
                    coordinates = feature['geometry']['coordinates_short']
                
                for a in coordinates:
                    for b in a:
                        b = simplify_coords(b, 1 / size / 10)
                        ToDrawPolygon(draw, b, size, p0, p1, currentStyle['color'], currentStyle['width'])
    del(draw)
    
    return image


def load_obj(name ):
    with open('C:\\Users\\79105\\Documents\\GitHub\\MapPy\\obj/' + name + '.pkl', 'rb') as f:
        return pickle.load(f)

data = load_obj('data')

styles = LoadStyles()


from sanic import Sanic
from sanic.response import json
from sanic import response
from sanic.request import RequestParameters
import random

app = Sanic()


@app.route("/")
def output(request):
	return response.file("C:\\Users\\79105\\Documents\\GitHub\\MapPy\\templates\\index.html")
	
@app.route("/docs/images/favicon.ico")
def output(request):
	return response.file("C:\\Users\\79105\\Documents\\GitHub\\MapPy\\678074-map-256.ico")



@app.route('/return-files/')
async def return_files_tut(request):
	#try:
	x=request.args.get('x')
	y=request.args.get('y')
	z=request.args.get('z')
	s=request.args.get('s')		
	print(x, y, z, s)
	
	s = x+y+z
	file_path = "C:\\Users\\79105\\Documents\\GitHub\\MapPy\\images\\" + s + ".png"
	
	if not os.path.exists(file_path):
		image = ToDrawPicture(int(x), int(y), int(z), (90, 0), (200, 110), 256, {2: True, 3: True, 6: True}, styles)
		image.save(file_path, "PNG")		
	
	return await response.file(file_path)
	#except Exception as e:
	#	return str(e)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)