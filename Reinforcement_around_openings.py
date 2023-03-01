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


#from Classes import *

#from Functions import *

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

class Opening:
	def __init__(self, id, srfs=0 ,cut=0, ends=0, local_coord=0, reb_lines=0, reb_vecs=0):
		self.id = id
		self.srfs = srfs
		self.ends = ends
		self.local_coord = local_coord
		self.reb_lines = reb_lines
		self.reb_vecs = reb_vecs
 

doc =  DocumentManager.Instance.CurrentDBDocument

# Input 
elem = UnwrapElement(IN[0])
anchoring = units_mm_project(IN[1])
rebar_diam_mm = IN[2]

# Modify input
rebar_diam = 'ø'+ str(int(rebar_diam_mm))
type_id = elem.GetTypeId()
elem_type = doc.GetElement(type_id)
family_name = elem_type.FamilyName

# True diameter for rebars
rebars = {'ø10': 11, 'ø12': 13.2,'ø16': 17.6,'ø20': 22, 'ø25': 27.4,'ø32': 35.2,}

# Get rebar covers
reb_covers = []
if family_name == "Basic Wall":
	reb_covers.append(units_internal_project(doc.GetElement(elem.get_Parameter(BuiltInParameter.CLEAR_COVER_EXTERIOR).AsElementId()).CoverDistance))
	reb_covers.append(units_internal_project(doc.GetElement(elem.get_Parameter(BuiltInParameter.CLEAR_COVER_INTERIOR).AsElementId()).CoverDistance))
	reb_covers.append(units_internal_project(doc.GetElement(elem.get_Parameter(BuiltInParameter.CLEAR_COVER_OTHER).AsElementId()).CoverDistance))
elif family_name == "Concrete-Rectangular-Beam":
	reb_covers.append(units_internal_project(doc.GetElement(elem.get_Parameter(BuiltInParameter.CLEAR_COVER_BOTTOM).AsElementId()).CoverDistance))
	reb_covers.append(units_internal_project(doc.GetElement(elem.get_Parameter(BuiltInParameter.CLEAR_COVER_TOP).AsElementId()).CoverDistance))
	reb_covers.append(units_internal_project(doc.GetElement(elem.get_Parameter(BuiltInParameter.CLEAR_COVER_OTHER).AsElementId()).CoverDistance))
	
# Get all Revit type openings
view = doc.ActiveView
openings = FilteredElementCollector(doc, view.Id).OfCategory(BuiltInCategory.OST_GenericModel).ToElements()
	
# Set options to extract geometry
opt = Options()
opt.ComputeReferences = False
opt.IncludeNonVisibleObjects = False
opt.DetailLevel = ViewDetailLevel.Medium

# Get dynamo geometry for element
elem_geo = elem.get_Geometry(opt)
elem_srfs = get_surfaces(elem_geo)

# Get dynamo geometry for openings
cnt = 0
all_openings = []
for opening in openings:
	open_geo = opening.get_Geometry(opt)
	srf = get_surfaces(open_geo)
	if srf != False:
		srfs = get_surfaces(open_geo)
		all_openings.append(Opening('opening{num}'.format(num=cnt),srfs))
		cnt += 1

# Sort out surfaces inside wall
for opening in all_openings:
	cut_list = []
	for srf in opening.srfs:
		pt = srf.PointAtParameter(0.5,0.5)
		for elem_srf in elem_srfs:
			dist = pt.DistanceTo(elem_srf)
			if dist <= 0.0001:
				cut_list.append(srf)
	opening.cut = cut_list

# Sort out surfaces outside wall
for i,opening in enumerate(all_openings):
	ends = []
	srf_pts = []
	vecs = []
	for srf in opening.srfs:
		if srf not in opening.cut:
			ends.append(srf)
			pt = srf.PointAtParameter(0.5,0.5)
			srf_pts.append(pt)
			if i==0:
				y_axis = Vector.ByTwoPoints(pt, srf.PointAtParameter(0.5,1))
				z_axis = Vector.ByTwoPoints(pt, srf.PointAtParameter(1,0.5))
	opening.ends = ends
	opening.reb_vecs = [Vector.ByTwoPoints(srf_pts[0],srf_pts[1]).ToRevitType(),Vector.ByTwoPoints(srf_pts[1],srf_pts[0]).ToRevitType()]
	origin = Line.ByStartPointEndPoint(srf_pts[0],srf_pts[1]).PointAtParameter(0.5)
	x_axis = Vector.ByTwoPoints(srf_pts[1], srf_pts[0])
	opening.local_coord = CoordinateSystem.ByOriginVectors(origin, x_axis, y_axis, z_axis)
	
# Get rebar curves
for opening in all_openings:
	coord = opening.local_coord
	ori = coord.Origin
	pt_y = 0
	pt_z = 0
	for srf in opening.cut:
		pts_y = ori.Project(srf, coord.YAxis)
		pts_z = ori.Project(srf, coord.ZAxis)
		if len(pts_y) != 0:
			pt_y = pts_y[0]
		if len(pts_z) != 0:
			pt_z = pts_z[0]
	w = Vector.ByTwoPoints(ori, pt_y).Length*2+ reb_covers[0]
	h = Vector.ByTwoPoints(ori, pt_z).Length*2+ reb_covers[0]
	plane = Plane.ByOriginNormal(ori, coord.XAxis)
	lines = Rectangle.ByWidthLength(plane, w, h).Explode()
	lines_long = [extend_curve(l, 0.6) for l in lines]
	pts = [l.PointAtParameter(0.5) for l in lines_long]
	
	
	
	dist=[reb_covers[-1]+units_mm_project(rebar_diam_mm)/2, reb_covers[-1]+(3.0/2.0)*units_mm_project(rebars[rebar_diam]),reb_covers[-1]+units_mm_project(rebar_diam_mm)/2, reb_covers[-1]+(3.0/2.0)*units_mm_project(rebars[rebar_diam])]
	
	
	reb_lines_list = []
	intersect_lines = [Line.ByStartPointDirectionLength(pt,coord.XAxis, 1000) for pt in pts]
	intersection_pts = []
	for line in intersect_lines:
		for elem_srf in elem_srfs:	
			if line.DoesIntersect(elem_srf):
				intersection_pts.append(line.Intersect(elem_srf)[0])		

	reb_lines_list.append([line.Translate(Vector.ByTwoPoints(pts[i], intersection_pts[i]), Vector.ByTwoPoints(pts[i], intersection_pts[i]).Length-dist[i]) for i,line in enumerate(lines_long)])			
	
	
	intersect_lines = [Line.ByStartPointDirectionLength(pt,coord.XAxis.Reverse(), 1000) for pt in pts]
	intersection_pts2 = []
	for line in intersect_lines:
		for elem_srf in elem_srfs:	
			if line.DoesIntersect(elem_srf):
				intersection_pts2.append(line.Intersect(elem_srf)[0])
				
	reb_lines_list.append([line.Translate(Vector.ByTwoPoints(pts[i], intersection_pts2[i]), Vector.ByTwoPoints(pts[i], intersection_pts2[i]).Length-dist[i]) for i,line in enumerate(lines_long)])
	
	for i,line_set in enumerate(reb_lines_list):
		for j,line in enumerate(line_set):
			for srf in elem_srfs:
				intersection_list = line.Intersect(srf)
				if intersection_list.Length != 0:
					splitted_lines = line.SplitByPoints(intersection_list)
					dists = []
					for line in splitted_lines:
						dists.append(ori.DistanceTo(line))
					min_val = min(dists)
					min_indx = dists.index(min_val)
					cut_line = splitted_lines[min_indx]
					reb_lines_list[i][j] = shorten_curve(cut_line, reb_covers[-1])
	opening.reb_lines = reb_lines_list
	
# Create rebars in Revit
test_mode = False
if test_mode == False:	
	TransactionManager.Instance.EnsureInTransaction(doc)
	
	# Get all rebar types
	all_rebar_types = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rebar).WhereElementIsElementType().ToElements()
	
	# Get rebar type for rebars
	for rebar_type in all_rebar_types:
		rebar_name = rebar_type.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM).AsString()
		if rebar_name == rebar_diam:
			bar_type = rebar_type
			break
	
	# Create rebars
	for opening in all_openings:
		both_sides = opening.reb_lines
		vecs = opening.reb_vecs
		for j,side in enumerate(both_sides):
			crvs = side
			if j%2 !=0:
				vec = vecs[0]
			else:
				vec = vecs[1]
			for j,line in enumerate(crvs):
				rebar = Structure.Rebar.CreateFromCurves(doc, Structure.RebarStyle.Standard, bar_type, None, None, elem, vec, [line.ToRevitType()], Structure.RebarHookOrientation.Right, Structure.RebarHookOrientation.Left, True, False)
				rebar.SetUnobscuredInView(view,1)
				rebar.SetSolidInView(view,1)
	TransactionManager.Instance.TransactionTaskDone()