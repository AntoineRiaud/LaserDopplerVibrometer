def dichotomic_search(f,xmin,xmax,f0=0,tol=1,growing=True):
    g = {True:1,False:-1}
    xmed = tol*int((xmax+xmin)/(2*tol))
    if xmed==xmax or xmed==xmin:
        return xmed
    else:
        if (g[growing]*(f(xmed)- f0))>0:
            return dichotomic_search(f,xmin,xmed,f0=f0,tol=tol,growing=growing)
        else:
            return dichotomic_search(f,xmed,xmax,f0=f0,tol=tol,growing=growing)