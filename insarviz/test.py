from pyproj import Proj, transform

inProj = Proj(init='epsg:3857')
outProj = Proj(init='epsg:32740')
x1,y1 = 366067,7650273
x2,y2 = transform(inProj,outProj,x1,y1)
print(x2,y2)