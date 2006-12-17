# Documentation builder stuff

HTML = 
PRE = 
CSS = 
IMAGES = 
WEBSITE = $(CSS) $(HTML) $(PRE) $(IMAGES)

# Distribution stuff
TAR = tar
TAROPTS = --exclude=.svn --exclude='*.pyc'
COMPRESS = bzip2 -f

PACKAGE := peppy
VERSION := $(shell grep __version__ $(PACKAGE).py|head -n1|cut -d \" -f 2)

EPYDOC = epydoc -v -v -v --no-sourcecode

srcdir = .
top_srcdir = .
top_builddir = .

distdir := $(PACKAGE)-$(VERSION)
top_distdir := $(distdir)

DISTMAIN = peppy.py
DISTMODS = buffers.py configprefs.py debug.py fundamental.py hexedit-plugin.py iofilter.py menudev.py plugin.py python-plugin.py singletonmixin.py stcinterface.py tabbedviewer.py test-plugin.py views.py wxemacskeybindings.py trac/core.py
DISTSRC = $(DISTMAIN) $(DISTMODS)
DISTDOCS = README ChangeLog gpl.txt
DISTFILES = $(DISTSRC) $(DISTDOCS) icons trac
DISTFILE_TESTS = 


.SUFFIXES:      .html.in .pre.in .html

.html.in.html: template.html.in mainmenu.html.in
	./Makedoc.py -m peppy -o $*.html -n mainMenu mainmenu.html.in -n htmlBody $*.html.in -t template.html.in

.pre.in.html: template.html.in mainmenu.html.in
	./Makedoc.py -m peppy -o $*.html -n mainMenu mainmenu.html.in -n preBody $*.pre.in -t template.html.in





all: doc

api/index.html: $(DISTSRC)
	./Makedoc.py -m peppy -d -o /tmp/peppy.py peppy.py
	$(EPYDOC) -o api --no-private --url 'http://www.flipturn.org/peppy/' /tmp/peppy.py $(DISTMODS)

README: README.pre.in
	./Makedoc.py -m peppy -o README README.pre.in



doc: README

html: $(HTML) $(PRE)

publish_html: html
	rsync -avuz $(WEBSITE) robm@peppy.sourceforge.net:/home/groups/p/py/peppy/htdocs

api: api/index.html

publish_api: api
	rsync -avuz api robm@peppy.sourceforge.net:/home/groups/p/py/peppy/htdocs

publish: publish_api publish_html


release: dist
	-mkdir -p archive
	cp $(distdir).tar.bz2 archive

dist: distdir
	-chmod -R a+r $(distdir)
	$(TAR) cvf $(distdir).tar $(TAROPTS) $(distdir)
	$(COMPRESS) $(distdir).tar
	-rm -rf $(distdir)

distdir: $(DISTFILES)
	-rm -rf $(distdir)
	mkdir $(distdir)
	-chmod 777 $(distdir)
	distdir=`cd $(distdir) && pwd`
	@for file in $(DISTFILES); do \
	  d=$(srcdir); \
	  if test -d $$d/$$file; then \
	    cp -pr $$d/$$file $(distdir)/$$file; \
	  else \
	    test -f $(distdir)/$$file \
	    || ln $$d/$$file $(distdir)/$$file 2> /dev/null \
	    || cp -p $$d/$$file $(distdir)/$$file || :; \
	  fi; \
	done
#	mkdir $(distdir)/website
#	./Makedoc.py -m peppy -r version cvs_version -d -o /tmp/peppy.py peppy.py
#	epydoc -o $(distdir)/website/api --no-private -u '../index.html' /tmp/peppy.py
#	mkdir $(distdir)/examples
#	cp $(DISTFILE_TESTS) $(distdir)/examples




clean:
	rm -rf *~ *.o *.exe build api README $(HTML) $(PRE) $(distdir)

.PHONY: print-% clean html publish_html api publish_api publish release dist distdir

print-%: ; @ echo $* = $($*)

