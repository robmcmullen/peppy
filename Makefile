# Documentation builder stuff

HTML = 
PRE = 
CSS = 
IMAGES = 
WEBSITE = $(CSS) $(HTML) $(PRE) $(IMAGES)

# Distribution stuff
TAR = tar
TAROPTS = --exclude=.git --exclude=.svn --exclude='*.pyc' --exclude='*~'
COMPRESS = bzip2 -f

PACKAGE := peppy
VERSION_CODENAME := $(shell grep Released ChangeLog|head -n1|cut -d '"' -f 2)
VERSION := $(shell grep Released ChangeLog|head -n1|cut -d '-' -f 2|cut -d ' ' -f 1)

EPYDOC = epydoc -v -v -v --no-sourcecode

srcdir = .
top_srcdir = .
top_builddir = .

distdir := $(PACKAGE)-$(VERSION)
top_distdir := $(distdir)

APPMAIN = peppy.py
WINBATCH = peppy.bat
SCRIPTMAIN = scripts/peppy
DISTMAIN = peppy/__init__.py

GIT_LIST = $(shell git-ls-files)
GIT_FILTER_OUT := %.in Makefile make-% peppy.bat setup.py svn-ls.py trac/% peppy/icons/%.png peppy/icons/%.ico %/
GIT_FILTERED := $(filter-out $(GIT_FILTER_OUT),$(GIT_LIST))
DISTSRC := $(filter %.py,$(GIT_FILTERED))
DISTFILES := README INSTALL $(GIT_FILTERED)
APIFILES := $(filter-out $(APPMAIN) $(DISTMAIN) tests/% demo/%,$(DISTSRC))


.SUFFIXES:      .html.in .pre.in .html

.html.in.html: template.html.in mainmenu.html.in
	./make-doc.py -m peppy -o $*.html -n mainMenu mainmenu.html.in -n htmlBody $*.html.in -t template.html.in

.pre.in.html: template.html.in mainmenu.html.in
	./make-doc.py -m peppy -o $*.html -n mainMenu mainmenu.html.in -n preBody $*.pre.in -t template.html.in





all: doc

README: README.pre.in ChangeLog
	./make-doc.py -m peppy -o README README.pre.in

INSTALL: INSTALL.pre.in ChangeLog
	./make-doc.py -m peppy -o INSTALL INSTALL.pre.in

doc: README INSTALL

html: $(HTML) $(PRE)

publish_html: html
	rsync -avuz $(WEBSITE) robm@peppy.sourceforge.net:/home/groups/p/py/peppy/htdocs

publish_api: api
	rsync -avuz api robm351@www.flipturn.org:flipturn.org/peppy/

release: dist
	-mkdir -p archive
	mv $(distdir).tar.bz2 archive

publish: api release
	rsync -avuz api archive robm351@www.flipturn.org:flipturn.org/peppy/


dist: distdir
	-chmod -R a+r $(distdir)
	rm -f $(distdir)/peppy/icons/iconmap.py
	rm -f $(distdir)/peppy/py2exe_plugins.py
	$(TAR) cvf $(distdir).tar $(TAROPTS) $(distdir)
	$(COMPRESS) $(distdir).tar
	-rm -rf $(distdir)

distdir:
	-rm -rf $(distdir)
	mkdir $(distdir)
	-chmod 777 $(distdir)
	tar cf - $(DISTFILES) | (cd $(distdir); tar xf -)
	chmod 644 $(distdir)/tests/*.py
	./make-doc.py -m peppy -o $(distdir)/README README.pre.in
	./make-doc.py -m peppy -o $(distdir)/INSTALL INSTALL.pre.in
	./make-doc.py -m peppy -o $(distdir)/setup.py setup.py.in
	rm $(distdir)/$(DISTMAIN)
	./make-doc.py -m peppy -d -o $(distdir)/$(DISTMAIN).tmp $(DISTMAIN)
	sed -e "s/svn-devel/$(VERSION)/" -e "s/svn-codename/$(VERSION_CODENAME)/" $(distdir)/$(DISTMAIN).tmp > $(distdir)/$(DISTMAIN)
	rm $(distdir)/$(DISTMAIN).tmp

	./make-icon-data.py -o $(distdir)/peppy/icons/iconmap.py
	./make-py2exe-plugin-list.py -o $(distdir)/peppy/py2exe_plugins.py

	mkdir $(distdir)/scripts
	cp $(distdir)/$(APPMAIN) $(distdir)/$(SCRIPTMAIN)
	cp $(WINBATCH) $(distdir)/scripts

api: distdir
	(cd $(distdir); $(EPYDOC) -o docs/api --no-private --url 'http://www.flipturn.org/peppy/' $(DISTMAIN) $(APIFILES)) | tee epydoc.out



clean:
	rm -rf *~ *.o *.exe build api README $(HTML) $(PRE) $(distdir)

.PHONY: print-% clean html publish_html api publish_api publish release dist distdir

print-%: ; @ echo $* = $($*)

