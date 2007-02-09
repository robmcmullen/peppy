# Documentation builder stuff

HTML = 
PRE = 
CSS = 
IMAGES = 
WEBSITE = $(CSS) $(HTML) $(PRE) $(IMAGES)

# Distribution stuff
TAR = tar
TAROPTS = --exclude=.svn --exclude='*.pyc' --exclude='*~'
COMPRESS = bzip2 -f

PACKAGE := peppy
VERSION := $(shell grep Released ChangeLog|head -n1|cut -d '-' -f 2)

EPYDOC = epydoc -v -v -v --no-sourcecode

srcdir = .
top_srcdir = .
top_builddir = .

distdir := $(PACKAGE)-$(VERSION)
top_distdir := $(distdir)

DISTMAIN = peppy.py
#DISTMODS = buffers.py configprefs.py debug.py fundamental.py gotoline.py hexedit-plugin.py iofilter.py menudev.py minibuffer.py plugin.py python-plugin.py shell.py singletonmixin.py stcinterface.py tabbedviewer.py test-plugin.py views.py wxemacskeybindings.py
#DISTSRC = $(DISTMAIN) $(DISTMODS)
#DISTDOCS = README ChangeLog LICENSE
#DISTFILES = $(DISTSRC) $(DISTDOCS) icons trac tests nltk_lite pype
#DISTFILE_TESTS = 

SVN_LIST = $(shell svn ls -R)
#SVN_LIST := ChangeLog LICENSE Makedoc.py Makefile README.pre.in actions/ actions/__init__.py actions/gotoline.py actions/minibuffer.py buffers.py configprefs.py debug.py demos/ demos/__init__.py demos/actions.py demos/auitest.py demos/ngmenu.py icons/ icons/application.png icons/application_xp_terminal.png icons/arrow_turn_left.png icons/arrow_turn_right.png icons/blank.ico icons/bug_add.png icons/cross.png icons/cut.png icons/disk.png icons/disk_edit.png icons/folder_image.png icons/folder_page.png icons/green.gif icons/html.png icons/image.png icons/map_magnify.png icons/page.png icons/page_copy.png icons/page_white.png icons/page_white_c.png icons/page_white_cplusplus.png icons/page_white_picture.png icons/page_white_text.png icons/page_white_tux.png icons/paste_plain.png icons/picture.png icons/py.ico icons/red.gif icons/text_indent_remove_rob.png icons/text_indent_rob.png icons/tux.png icons/world.png icons/yellow.gif iconstorage.py iofilter.py major.py major_modes/ major_modes/__init__.py major_modes/fundamental.py major_modes/hexedit.py major_modes/python.py major_modes/shell.py menu.py menudev.py minor_modes/ minor_modes/__init__.py nltk_lite/ nltk_lite/__init__.py nltk_lite/chat/ nltk_lite/chat/__init__.py nltk_lite/chat/eliza.py nltk_lite/chat/iesha.py nltk_lite/chat/rude.py nltk_lite/chat/zen.py orderer.py peppy.py plugin.py plugins/ plugins/__init__.py plugins/about.py plugins/chatbots.py pype/ pype/__init__.py pype/codetree.py pype/exparse.py pype/findbar.py pype/parsers.py stcinterface.py tabbedviewer.py tests/ tests/test_iofilter.py tests/test_majormode.py tests/test_orderer.py trac/ trac/__init__.py trac/core.py wxemacskeybindings.py
SVN_FILTER_OUT := README.pre.in Makedoc.py %/
SVN_FILTERED := $(filter-out $(SVN_FILTER_OUT),$(SVN_LIST))
DISTSRC := $(filter %.py,$(SVN_FILTERED))
DISTFILES := README $(SVN_FILTERED)
DISTMODS := $(filter-out peppy.py,$(DISTSRC))


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
	rsync -avuz api robm351@www.flipturn.org:flipturn.org/peppy/

release: dist
	-mkdir -p archive
	mv $(distdir).tar.bz2 archive

publish: api release
	rsync -avuz api archive robm351@www.flipturn.org:flipturn.org/peppy/


dist: distdir
	-chmod -R a+r $(distdir)
	$(TAR) cvf $(distdir).tar $(TAROPTS) $(distdir)
	$(COMPRESS) $(distdir).tar
	-rm -rf $(distdir)

distdir: $(DISTFILES)
	-rm -rf $(distdir)
	mkdir $(distdir)
	-chmod 777 $(distdir)
	tar cf - $(DISTFILES) | (cd $(distdir); tar xf -)
	rm $(distdir)/$(DISTMAIN)
	sed -e "s/svn-devel/$(VERSION)/" $(DISTMAIN)>$(distdir)/$(DISTMAIN)



clean:
	rm -rf *~ *.o *.exe build api README $(HTML) $(PRE) $(distdir)

.PHONY: print-% clean html publish_html api publish_api publish release dist distdir

print-%: ; @ echo $* = $($*)

