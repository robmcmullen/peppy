/* peppy Copyright (c) 2006-2007 Rob McMullen
   Licenced under the GPL; see http://www.flipturn.org/peppy for more info
*/
#include "Python.h"
#include "libnumarray.h"

#include <stdio.h>
#include <stdlib.h>
#include <math.h>

static PyObject *_Error;

static int CalculateSameOrderInt16(PyArrayObject *one, PyArrayObject *two,
    PyArrayObject *data, int *maxvalue, int *maxdiff,
    long nbins, long width, long bandBoundary,
    double scale1, double scale2)
{
    float sum=0;
    int band=0;
    int count=0;
    int progress=0;
    int showprog=100000;
    int num=0;
    int i;
    int sizex = one->dimensions[0];
    
    printf("In Int16!\nflat array size=%d\n",sizex);

    int s1=(int)scale1;
    int s2=(int)scale2;
    
    for(i=0; i<sizex; i++) {
	  /* scale values to range 0-10000 */
	int val1=NA_GET1(one, Int16, i)*s1;
	int val2=NA_GET1(two, Int16, i)*s2;
	if (abs(val1)>abs(val2) && abs(val1)>maxvalue[band])
	    maxvalue[band]=abs(val1);
	else if (abs(val2)>maxvalue[band])
	    maxvalue[band]=abs(val2);
	
	int bin=abs(val1-val2);
	if (bin>maxdiff[band]) maxdiff[band]=bin;
	
	if (bin>nbins) bin=nbins-1;
	  //int accum=NA_get2_Int64(data,band,bin)+1;
	  //NA_set2_Int64(data,band,bin,accum);
	int accum=NA_GET2(data,Int32,band,bin)+1;
	NA_SET2(data,Int32,band,bin,accum);
	  //printf("i=%d band=%d bin=%d val=%f\n",i,band,bin,val);
	count++;
	if (count>=bandBoundary) {
	    count=0;
	    band++;
	    if (band>=width) band=0;
	}
	progress++;
	if (progress>=showprog) {
	    fputc('#',stdout);
	    fflush(stdout);
	    progress=0;
	}
	num++;
    }
    fputc('\n',stdout);
    fflush(stdout);

    return num;
}

static int CalculateSameOrderGeneric(PyArrayObject *one, PyArrayObject *two,
    PyArrayObject *data, int *maxvalue, int *maxdiff,
    long nbins, long width, long bandBoundary,
    double scale1, double scale2)
{
    float sum=0;
    int band=0;
    int count=0;
    int progress=0;
    int showprog=100000;
    int num=0;
    int i;
    int sizex = one->dimensions[0];
    
    printf("flat array size=%d\n",sizex);
    
    for(i=0; i<sizex; i++) {
	  /* scale values to range 0-10000 */
	float val1=NA_get1_Float64(one, i)*scale1;
	float val2=NA_get1_Float64(two, i)*scale2;
	float val=abs(val1-val2);
	int bin=(int)val;
	if (bin>nbins) bin=nbins-1;
	  //int accum=NA_get2_Int64(data,band,bin)+1;
	  //NA_set2_Int64(data,band,bin,accum);
	int accum=NA_GET2(data,Int32,band,bin)+1;
	NA_SET2(data,Int32,band,bin,accum);
	  //printf("i=%d band=%d bin=%d val=%f\n",i,band,bin,val);
	count++;
	if (count>=bandBoundary) {
	    count=0;
	    band++;
	    if (band>=width) band=0;
	}
	progress++;
	if (progress>=showprog) {
	    fputc('#',stdout);
	    fflush(stdout);
	    progress=0;
	}
	num++;
    }
    fputc('\n',stdout);
    fflush(stdout);

    return num;
}


static int CalculateSameOrder(PyArrayObject *one, PyArrayObject *two,
    PyArrayObject *data, int *maxvalue, int *maxdiff,
    long nbins, long width, long bandBoundary,
    double scale1, double scale2)
{
    int num=0;
    
    printf("type: one=%d two=%d\n",one->descr->type_num,two->descr->type_num);
    if (one->descr->type_num==two->descr->type_num) {
	  /* OK, they're both the same type.  Now, what are they? */
	if (one->descr->type_num==tInt16) {
	    num=CalculateSameOrderInt16(one,two,data,maxvalue,maxdiff,nbins,width,bandBoundary,scale1,scale2);
	}
	else {
	    num=CalculateSameOrderGeneric(one,two,data,maxvalue,maxdiff,nbins,width,bandBoundary,scale1,scale2);
	}
    }
    else {
	num=CalculateSameOrderGeneric(one,two,data,maxvalue,maxdiff,nbins,width,bandBoundary,scale1,scale2);
    }
    
    return num;
}

/* Function pointer definitions that will be used in CalculateGeneric */
typedef void (*flatloc_t)(long, long *,long *,long *,long, long, long);
typedef long (*locflat_t)(long, long, long, long, long, long);

static void BIPflatToLocation(long pos,long *sample,long *line,long *band,
    long samples,long lines,long bands) {
    
    *line=pos/(bands*samples);
    long temp=pos%(bands*samples);
    *sample=temp/bands;
    *band=temp%bands;
}

static long BIPlocationToFlat(long sample,long line,long band,
    long samples,long lines,long bands) {

    long pos=line*bands*samples + sample*bands + band;
    return pos;
}

    
static void BILflatToLocation(long pos,long *sample,long *line,long *band,
    long samples,long lines,long bands) {

    *line=pos/(bands*samples);
    long temp=pos%(bands*samples);
    *band=temp/samples;
    *sample=temp%samples;
}

static long BILlocationToFlat(long sample,long line,long band,
    long samples,long lines,long bands) {

    long pos=line*bands*samples + band*samples + sample;
    return pos;
}


static void BSQflatToLocation(long pos,long *sample,long *line,long *band,
    long samples,long lines,long bands) {

    *band=pos/(lines*samples);
    long temp=pos%(lines*samples);
    *line=temp/samples;
    *sample=temp%samples;
}

static long BSQlocationToFlat(long sample,long line,long band,
    long samples,long lines,long bands) {

    long pos=band*lines*samples + line*samples + sample;
    return pos;
}

    

static int CalculateGeneric(PyArrayObject *one, PyArrayObject *two,
    PyArrayObject *data, int *maxvalue, int *maxdiff,
    long nbins, long width, long bandBoundary,
    PyObject *cube1, PyObject *cube2,
    double scale1, double scale2,
    flatloc_t flatToLocation, locflat_t locationToFlat)
{
    PyObject *tmp;
    
    float sum=0;
    int band=0;
    int count=0;
    int progress=0;
    int showprog=100000;
    int num=0;
    int i1,i2;
    int sizex = one->dimensions[0];
    printf("flat array size=%d\n",sizex);
    
    tmp=PyObject_GetAttrString(cube1,"samples");
    long samples=PyInt_AsLong(tmp);
    Py_XDECREF(tmp);
    
    tmp=PyObject_GetAttrString(cube1,"lines");
    long lines=PyInt_AsLong(tmp);
    Py_XDECREF(tmp);
    
    tmp=PyObject_GetAttrString(cube1,"bands");
    long bands=PyInt_AsLong(tmp);
    Py_XDECREF(tmp);
    
    long sample,line,bandcube1;

    
    for(i1=0; i1<sizex; i1++) {
	float val1=NA_get1_Float64(one, i1)*scale1;
	(*flatToLocation)(i1,&sample,&line,&bandcube1,samples,lines,bands);
	i2=(*locationToFlat)(sample,line,bandcube1,samples,lines,bands);
	float val2=NA_get1_Float64(two, i2)*scale2;
	float val=abs(val1-val2);
	int bin=(int)val;
	if (bin>nbins) bin=nbins-1;
	int accum=NA_get2_Int64(data,band,bin)+1;
	NA_set2_Int64(data,band,bin,accum);
	  //printf("i1=%d i2=%d band=%d bin=%d val=%f\n",i1,i2,band,bin,val);
	count++;
	if (count>=bandBoundary) {
	    count=0;
	    band++;
	    if (band>=width) band=0;
	}
	progress++;
	if (progress>=showprog) {
	    fputc('#',stdout);
	    fflush(stdout);
	    progress=0;
	}
	num++;
    }
    fputc('\n',stdout);
    fflush(stdout);
    
    return num;
}



static PyObject *Py_CubeHistogram(PyObject *obj, PyObject *args)
{
    PyObject       *cube1=Py_None,*cube2=Py_None,*hist=Py_None, *tmp;
    PyArrayObject  *one, *two;

    if (!PyArg_ParseTuple(args, "OOO", &cube1, &cube2, &hist))
	return PyErr_Format(_Error, 
	    "CubeHistogram: Invalid parameters.");


    PyObject *oone=PyObject_CallMethod(cube1,"getFlatView",NULL);
    PyObject *otwo=PyObject_CallMethod(cube2,"getFlatView",NULL);
    if (!oone || !otwo) return NULL;

    one = NA_InputArray(oone,   tAny, UNCONVERTED);
    two = NA_InputArray(otwo,   tAny, UNCONVERTED);
    
    if (!one || !two || !hist) return NULL;
    
    if (!NA_ShapeEqual(one, two))
	return PyErr_Format(_Error,
	    "CubeHistogram: need identical cube shapes.");

      /* Get some attributes from the Histogram object */
    tmp=PyObject_GetAttrString(hist,"width");
    long width=PyInt_AsLong(tmp);
    Py_XDECREF(tmp);
    
    tmp=PyObject_GetAttrString(hist,"nbins");
    long nbins=PyInt_AsLong(tmp);
    Py_XDECREF(tmp);

    tmp=PyObject_GetAttrString(hist,"data");
    PyArrayObject *data=NA_IoArray(tmp,tAny,UNCONVERTED);
    Py_XDECREF(tmp);
    
    printf("histogram: width=%d nbins=%d\n",width,nbins);
    
    tmp=PyObject_GetAttrString(cube1,"interleave");
    char *i1=PyString_AsString(tmp);
    Py_XDECREF(tmp);
    
    tmp=PyObject_GetAttrString(cube2,"interleave");
    char *i2=PyString_AsString(tmp);
    Py_XDECREF(tmp);

    tmp=PyObject_GetAttrString(cube1,"scale_factor");
    double scale1=10000.0/PyFloat_AsDouble(tmp);
    Py_XDECREF(tmp);
    
    tmp=PyObject_GetAttrString(cube2,"scale_factor");
    double scale2=10000.0/PyFloat_AsDouble(tmp);
    Py_XDECREF(tmp);

    tmp=PyObject_CallMethod(cube1,"getBandBoundary",NULL);
    long bandBoundary=PyInt_AsLong(tmp);
    Py_XDECREF(tmp);
    printf("band boundary=%d\n",bandBoundary);

    int *maxvalue,*maxdiff;
    maxvalue=(int *)calloc(width,sizeof(int));
    maxdiff=(int *)calloc(width,sizeof(int));
    

    int ret;
    if (strcmp(i1,i2)==0) {
	ret=CalculateSameOrder(one,two,data,maxvalue,maxdiff,nbins,width,bandBoundary,scale1,scale2);
    }
    else {
	flatloc_t flat2loc;
	locflat_t loc2flat;
	
	if (strcmp(i1,"bip")==0) flat2loc=BIPflatToLocation;
	else if (strcmp(i1,"bil")==0) flat2loc=BILflatToLocation;
	else if (strcmp(i1,"bsq")==0) flat2loc=BSQflatToLocation;
	else flat2loc=NULL;

	if (strcmp(i2,"bip")==0) loc2flat=BIPlocationToFlat;
	else if (strcmp(i2,"bil")==0) loc2flat=BILlocationToFlat;
	else if (strcmp(i2,"bsq")==0) loc2flat=BSQlocationToFlat;
	else flat2loc=NULL;
	
	ret=CalculateGeneric(one,two,data,maxvalue,maxdiff,nbins,width,bandBoundary,cube1,cube2,scale1,scale2,flat2loc,loc2flat);
    }
    
    tmp=PyObject_GetAttrString(hist,"maxvalue");
    PyArrayObject *list=NA_IoArray(tmp,tAny,UNCONVERTED);
    Py_XDECREF(tmp);
    int band;
    for (band=0; band<width; band++)
	NA_SET1(list, Int32, band, maxvalue[band]);
    Py_XDECREF(list);

    tmp=PyObject_GetAttrString(hist,"maxdiff");
    list=NA_IoArray(tmp,tAny,UNCONVERTED);
    Py_XDECREF(tmp);
    for (band=0; band<width; band++)
	NA_SET1(list, Int32, band, maxdiff[band]);
    Py_XDECREF(list);
    
    Py_XDECREF(cube1);
    Py_XDECREF(cube2);
    Py_XDECREF(oone);
    Py_XDECREF(otwo);
    Py_XDECREF(one);
    Py_XDECREF(two);
    Py_XDECREF(data);
    
    PyObject *result = Py_BuildValue("i",ret);
    return result;
}

static PyMethodDef _utilsMethods[] = {
        {"CubeHistogram", Py_CubeHistogram, METH_VARARGS, 
         "CubeHistogram(cube1,cube2,hist) differences two cubes and stores the result in the histogram."},
        {NULL, NULL} /* Sentinel */
};



/* platform independent*/
#ifdef MS_WIN32
__declspec(dllexport)
#endif

void init_utils(void) {
        PyObject *m, *d;
        m = Py_InitModule("_utils", _utilsMethods);
        d = PyModule_GetDict(m);
        _Error = PyErr_NewException("_utils.error", NULL, NULL);
        PyDict_SetItemString(d, "error", _Error);
        import_libnumarray();
}
