# Documentation builder stuff

HTML = web/index.html web/about.html web/faq.html web/download.html web/thanks.html web/screenshots.html web/README.html web/ChangeLog.html web/manual
PRE = 
CSS = web/css web/js
IMAGES = web/peppy-web-logo.png web/0.3 web/0.6 web/0.7 web/*.png
WEBSITE = $(CSS) $(HTML) $(PRE) $(IMAGES)
AUX_LOCALE_DIRS = /opt/python/taskcoach/i18n.in /opt/wx/src/wxPython/wx/tools/Editra/locale /opt/python/ulipad/lang /usr/share/locale /usr/kde/3.5/share/locale

# Distribution stuff
TAR = tar
TAROPTS = --exclude=.git --exclude=.svn --exclude='*.pyc' --exclude='*~'
COMPRESS = bzip2 -f

PACKAGE := peppy
VERSION := $(shell python make-changelog.py  --version)

EPYDOC = epydoc -v -v -v --no-sourcecode --debug

srcdir = .
top_srcdir = .
top_builddir = .

distdir := $(PACKAGE)-$(VERSION)
top_distdir := $(distdir)

APPMAIN = run.py
WINBATCH = peppy.bat
SCRIPTMAIN = scripts/peppy
DISTMAIN = peppy/__init__.py

DISTFILES := AUTHORS ChangeLog docs FAQ INSTALL LICENSE.* NEWS README TODO peppy $(APPMAIN) peppy.bat setup_mac.py tests



.SUFFIXES:      .html.in .pre.in .html

.html.in.html: web/template.html.in web/mainmenu.html.in
	./make-doc.py -m peppy -o $*.html -n mainMenu web/mainmenu.html.in -n htmlBody $*.html.in -t web/template.html.in

.pre.in.html: web/template.html.in web/mainmenu.html.in
	./make-doc.py -m peppy -o $*.html -n mainMenu web/mainmenu.html.in -n preBody $*.pre.in -t web/template.html.in





all: doc

README: README.pre.in ChangeLog
	./make-doc.py -m peppy -o README README.pre.in

INSTALL: INSTALL.pre.in ChangeLog
	./make-doc.py -m peppy -o INSTALL INSTALL.pre.in

doc: README INSTALL

html: $(HTML) $(PRE) README.html README doc
	cp README.html web/
	(cd manual; make html)
	mkdir -p web/manual
	rsync -avuz manual/_build/html/ web/manual/

peppy/_peppy_version.py:
	./make-changelog.py -m peppy

web/thanks.html.in:
	python $(APPMAIN) --no-server --no-splash --thanks > web/thanks.html.in
web/screenshots.html.in: web/0.*
	(cd web; photo-album.py --nodatedir 0.*; photo-index.py -a -b -r -o screenshots.html.in)
web/ChangeLog.html.in: ChangeLog
	./make-doc.py -c -m peppy -o web/ChangeLog.html.in ChangeLog

$(HTML): web/template.html.in web/mainmenu.html.in web/ChangeLog.html.in ChangeLog peppy/_peppy_version.py

publish_html: html
	rsync -avuz $(WEBSITE) robm351@www.flipturn.org:peppy.flipturn.org/

publish_api: api
	rsync -avuz api robm351@www.flipturn.org:peppy.flipturn.org/

release: dist
	-mkdir -p archive
	mv $(distdir).tar.bz2 archive
	
splash:
	img2py -u graphics/peppy-splash.png peppy/splash_image.py

publish: api html
	rsync -avuz $(WEBSITE) archive robm351@www.flipturn.org:peppy.flipturn.org/

locale-full-rebuild:
	i18n.in/make-podict.py -a i18n.in -o peppy/i18n i18n.in/messages.pot $(AUX_LOCALE_DIRS)

locale:
	i18n.in/make-podict.py -f -a i18n.in -o peppy/i18n i18n.in/messages.pot

dist: distdir
	-chmod -R a+r $(distdir)
	rm -f $(distdir)/peppy/icons/iconmap.py
	rm -f $(distdir)/peppy/py2exe_plugins.py
	$(TAR) cvf $(distdir).tar $(TAROPTS) $(distdir)
	$(COMPRESS) $(distdir).tar
	-rm -rf $(distdir)

eggs:
	./plugins/egg-utils.py -d ./plugins/build -k egg

distdir: peppy/_peppy_version.py
	./make-doc.py -m peppy -o README README.pre.in
	./make-doc.py -m peppy -o INSTALL INSTALL.pre.in
	-rm -rf $(distdir)
	
	# Force setup to use MANIFEST.in
	-rm -f MANIFEST
	python setup.py sdist -k
	(cd $(distdir)/manual; make)
	-cp $(distdir)/manual/_build/latex/*.pdf $(distdir)
	rm -rf $(distdir)/manual
	chmod 644 $(distdir)/tests/*.py
	
	-cp ./plugins/build/*.egg $(distdir)/peppy/plugins/eggs
	
	./make-doc.py -m peppy -o $(distdir)/py2exe/win-installer.nsi $(distdir)/py2exe/win-installer.nsi.in

nsis:
	./make-doc.py -m peppy -o $(distdir)/py2exe/win-installer.nsi $(distdir)/py2exe/win-installer.nsi.in

api: distdir
	(cd $(distdir); $(EPYDOC) -o docs/api --exclude "peppy\.editra\..+" --no-private --url 'http://peppy.flipturn.org/' peppy) 2>&1 | tee epydoc.out
	rm -rf api
	mv $(distdir)/docs/api .



clean:
	rm -rf *~ *.o *.exe build api README $(HTML) $(PRE) $(distdir)

.PHONY: print-% clean html publish_html api publish_api publish release dist distdir

print-%: ; @ echo $* = $($*)

