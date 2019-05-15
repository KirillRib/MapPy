import geojson
from PIL import Image, ImageDraw, ImageFont
from pyproj import Proj, transform
import numpy as np
from simplification.cutil import simplify_coords, simplify_coords_vw, simplify_coords_vwp
import aggdraw
import copy
import timeit
import yaml
import pickle
import os.path
import sqlite3

#Генератор изображений
DefaultStyle = {'color': 'red', 'width': 2}
sizeOfShortCoordinates = 0.001

rectanglesList = []

conn = sqlite3.connect("MapPy.db")
cursor = conn.cursor()

def save_obj(obj, name):
    with open('obj/'+ name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)
def load_obj(name ):
    with open('obj/' + name + '.pkl', 'rb') as f:
        return pickle.load(f)




def LoadStyles(fileName="styles.yaml", encoding='utf-8'):
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

def ToConvertCoordinates(coordinatesArray):
    coordinatesArray = np.array(coordinatesArray)
    
    
    coordinatesArray[coordinatesArray < 0] += 360
    coordinatesArray -=30

    
    b=transform(proj_in, proj_out, coordinatesArray[:,0], coordinatesArray[:,1])
    coordinatesArray[:,0] = 90+b[0]/200000+15
    coordinatesArray[:,1] = 90-b[1]/100000
    
    return coordinatesArray



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


def isIntersectionRectangleWithRectanglesArray(a, rectanglesArray):
    intersection = False
    for b in rectanglesArray:
        intersection = isIntersectionRectangles(a, b)
        if intersection:
            break
    return intersection
    
def isIntersectionRectangles(a, b):
    return not (a[0][1] > b[1][1] or a[1][1] < b[0][1] or a[1][0] < b[0][0] or a[0][0] > b[1][0])
    

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
    
    
    availableLevelDictionary = {2: True, 3: True, 4: False, 5: False, 6: False}
    for i in range(2, z+3):
        availableLevelDictionary[i] = True
    print(availableLevelDictionary)
    
    image = Image.new("RGBA", (int(W),int(H)), (250,250,255,255))
    draw = ImageDraw.Draw(image)
    
    for i in reversed(range(len(data))):
        dataLevel = data[i]
        if activeLevelDictionary.get(i)!=None and activeLevelDictionary[i] and availableLevelDictionary[i]:
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
    
    global rectanglesList
    rectanglesList = []
    
    
    norm_P0 = ToNormalizeCoordinates(copy.copy(p0), p0, size)
    norm_P1 = ToNormalizeCoordinates(copy.copy(p1), p0, size)

    sqlCities = "SELECT name, x, y FROM GeographicalObjects WHERE x > ? and x < ? and y > ? and y < ? and admin_level == ? ORDER BY priority DESC LIMIT 30;"
    cursor.execute(sqlCities, (norm_P0[0], norm_P1[0], norm_P0[1], norm_P1[1], 1 + z))
    DravAreaNames(draw, size, p0, cursor.fetchall(), 10)
    
    if z > 0:
        sqlCities = "SELECT name, x, y FROM GeographicalObjects WHERE x > ? and x < ? and y > ? and y < ? and admin_level == 7 ORDER BY priority DESC LIMIT 30;"
        cursor.execute(sqlCities, (norm_P0[0], norm_P1[0], norm_P0[1], norm_P1[1]))
        DravCities(draw, size, p0, cursor.fetchall(), 4, 10)
    
    
    del(draw)
    
    return image

def DravCities(draw, size, p0, names, R, textSize):
    font = ImageFont.truetype("Roboto-Regular.ttf", textSize, encoding='UTF-8')

    for name in names:
        x = name[1]
        y = name[2]
        x, y = ToNormalizeCoordinates((x, y), p0, size)
        
        r = [[x-textSize/2, y-textSize/2], [x+textSize * len(name[0]) / 1.5, y+textSize]]
        if isIntersectionRectangleWithRectanglesArray(r, rectanglesList):
            #draw.rectangle([r[0][0], r[0][1], r[1][0], r[1][1]], outline=(64,128,255,128))       
            continue
        rectanglesList.append(r)
        
        draw.ellipse((x-R, y-R, x+R, y+R), fill=(64,128,255,128))
        draw.text((x+textSize/4,y), name[0], font=font, fill=(107, 35, 178,0), encoding='UTF-8')


def DravAreaNames(draw, size, p0, names, textSize):
    font = ImageFont.truetype("Roboto-Regular.ttf", textSize, encoding='UTF-8')

    for name in names:
        x = name[1]
        y = name[2]
        x, y = ToNormalizeCoordinates((x, y), p0, size)
        
        r = [[x-textSize * len(name[0]) / 3, y-textSize/3], [x+textSize * len(name[0]) / 3, y+textSize/3*4]]
        if isIntersectionRectangleWithRectanglesArray(r, rectanglesList):
                
            continue
        rectanglesList.append(r)
        #draw.rectangle([r[0][0], r[0][1], r[1][0], r[1][1]], outline=(64,128,255,128))   
        draw.text((r[0][0],r[0][1]), name[0], font=font, fill=(54, 216, 86), encoding='UTF-8')


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
		image = ToDrawPicture(int(x), int(y), int(z), (90, 0), (200, 110), 256, {2: True, 3: True, 4: True, 5: True, 6: True}, styles)
		image.save(file_path, "PNG")		
	
	return await response.file(file_path)
	#except Exception as e:
	#	return str(e)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)