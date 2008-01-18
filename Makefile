# Documentation builder stuff

HTML = web/index.html web/about.html web/faq.html web/download.html web/thanks.html web/screenshots.html web/README.html
PRE = 
CSS = web/css web/js
IMAGES = web/peppy-web-logo.png web/0.3 web/0.6 web/0.7
WEBSITE = $(CSS) $(HTML) $(PRE) $(IMAGES)

# Distribution stuff
TAR = tar
TAROPTS = --exclude=.git --exclude=.svn --exclude='*.pyc' --exclude='*~'
COMPRESS = bzip2 -f

PACKAGE := peppy
VERSION_CODENAME := $(shell grep Released ChangeLog|head -n1|cut -d '"' -f 2)
VERSION := $(shell grep Released ChangeLog|head -n1|cut -d '-' -f 2|cut -d ' ' -f 1)

EPYDOC = epydoc -v -v -v --no-sourcecode --debug

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
GIT_FILTER_OUT := %.in Makefile make-% peppy.bat setup.py svn-ls.py trac/% graphics/% peppy/icons/% %/ web/%
GIT_FILTERED := $(filter-out $(GIT_FILTER_OUT),$(GIT_LIST))
DISTSRC := $(filter %.py,$(GIT_FILTERED))
DISTFILES := README INSTALL $(GIT_FILTERED)
APIFILES := $(filter-out $(APPMAIN) $(DISTMAIN) tests/% demo/%,$(DISTSRC))


.SUFFIXES:      .html.in .pre.in .html

.html.in.html: web/template.html.in web/mainmenu.html.in
	./make-doc.py -m peppy -o $*.html -k codename "$(VERSION_CODENAME)" -n mainMenu web/mainmenu.html.in -n htmlBody $*.html.in -t web/template.html.in

.pre.in.html: web/template.html.in web/mainmenu.html.in
	./make-doc.py -m peppy -o $*.html -n mainMenu web/mainmenu.html.in -n preBody $*.pre.in -t web/template.html.in





all: doc

README: README.pre.in ChangeLog
	./make-doc.py -m peppy -o README README.pre.in

INSTALL: INSTALL.pre.in ChangeLog
	./make-doc.py -m peppy -o INSTALL INSTALL.pre.in

doc: README INSTALL

html: $(HTML) $(PRE) README.html doc
	cp README.html web/
web/thanks.html.in:
	python peppy.py --no-server --no-splash --thanks > web/thanks.html.in
web/screenshots.html.in: web/0.*
	(cd web; photo-album.py --nodatedir 0.*; photo-index.py -a -b -r -o screenshots.html.in)
$(HTML): web/template.html.in web/mainmenu.html.in ChangeLog

publish_html: html
	rsync -avuz $(WEBSITE) robm351@www.flipturn.org:peppy.flipturn.org/

publish_api: api
	rsync -avuz api robm351@www.flipturn.org:peppy.flipturn.org/

release: dist
	-mkdir -p archive
	mv $(distdir).tar.bz2 archive
	
splash:
	img2py -u graphics/peppy-splash.png peppy/splash_image.py

publish: api release
	rsync -avuz $(WEBSITE) archive robm351@www.flipturn.org:peppy.flipturn.org/


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
	
	./make-icon-data.py -o $(distdir)/peppy/iconmap.py
	
	cp win-executable.nsi $(distdir)
	./make-doc.py -m peppy -o $(distdir)/win-installer.nsi win-installer.nsi.in
	
	mkdir $(distdir)/scripts
	cp $(distdir)/$(APPMAIN) $(distdir)/$(SCRIPTMAIN)
	cp $(WINBATCH) $(distdir)/scripts

nsis:
	./make-doc.py -m peppy -o $(distdir)/win-installer.nsi win-installer.nsi.in

api: distdir
	(cd $(distdir); $(EPYDOC) -o docs/api --exclude "peppy\.editra\..+" --no-private --url 'http://peppy.flipturn.org/' peppy) 2>&1 | tee epydoc.out
	rm -rf api
	mv $(distdir)/docs/api .


clean:
	rm -rf *~ *.o *.exe build api README $(HTML) $(PRE) $(distdir)

.PHONY: print-% clean html publish_html api publish_api publish release dist distdir

print-%: ; @ echo $* = $($*)

