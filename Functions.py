import clr

clr.AddReference("RevitServices")
import RevitServices
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

clr.AddReference("RevitNodes")
import Revit
clr.ImportExtensions(Revit.Elements)
clr.ImportExtensions(Revit.GeometryConversion)

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
import Autodesk.Revit.DB.Solid as SOLID

clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript.Geometry import *


# Unit conversion functions
def units_internal_project(num):
	display_units = doc.GetUnits().GetFormatOptions(SpecTypeId.Length).GetUnitTypeId()
	return UnitUtils.ConvertFromInternalUnits(float(num), display_units)
	
def units_mm_project(num):
	display_units = doc.GetUnits().GetFormatOptions(SpecTypeId.Length).GetUnitTypeId()
	return UnitUtils.Convert(float(num), UnitTypeId.Millimeters, display_units)
	
def units_m_feet(num):
	return UnitUtils.Convert(float(num), UnitTypeId.Meters, UnitTypeId.Feet)
	
def units_internal_m(num): 
	return UnitUtils.ConvertFromInternalUnits(float(num), UnitTypeId.Meters)
	
def units_m_project(num):
	display_units = doc.GetUnits().GetFormatOptions(SpecTypeId.Length).GetUnitTypeId()
	return UnitUtils.Convert(float(num), UnitTypeId.Meters, display_units)


# Gets dynamo surfaces from Revit surfaces
def get_surfaces(geometry):
	srfs_list = False
	for geo in geometry:
		if isinstance(geo, SOLID):
			srfs = []
			if isinstance(geo, SOLID):
				for face in geo.Faces:
					srfs.extend(face.ToProtoType())
			if srfs:		
				srfs_list = srfs
		if isinstance(geo, GeometryInstance):
			geosymbs = geo.GetInstanceGeometry()
			for geoelem in geosymbs:
				srfs = []
				if isinstance(geoelem,SOLID):
					for face in geoelem.Faces:
						srfs.extend(face.ToProtoType())
				if srfs:
					srfs_list = srfs
	return srfs_list

# Extends a curv in both ends
def extend_curve(crv, dist):
	st = crv.StartPoint
	en = crv.EndPoint
	vec = Vector.ByTwoPoints(st,en)
	st_t = st.Translate(vec, -dist)
	en_t = en.Translate(vec,dist)
	return Line.ByStartPointEndPoint(st_t,en_t)

# Shorts a curve in both ends
def shorten_curve(crv, dist):
	st_pt = crv.StartPoint
	en_pt = crv.EndPoint
	vec = Vector.ByTwoPoints(st_pt,en_pt)
	short_crv = Line.ByStartPointEndPoint(st_pt.Translate(vec,dist), en_pt.Translate(vec,-dist))
	return short_crv