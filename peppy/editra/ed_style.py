###############################################################################
# Name: ed_style.py                                                           #
# Purpose: Editra's style management system. Implements the interpretation of #
#          Editra Style Sheets to the StyledTextCtrl.                         #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2008 Cody Precord <staff@editra.org>                         #
# License: wxWindows License                                                  #
###############################################################################

"""
Provides a system for managing styles in the text control. Compiles the data
in an Editra Style Sheet to a format that Scintilla can understand. The
specification of Editra Style Sheets that this module implements can be found
either in the _docs_ folder of the source distribution or on Editra's home page
U{http://editra.org/?page=docs&doc=ess_spec}.

@summary: Style management system for managing the syntax highlighting of all
          buffers

"""

__author__ = "Cody Precord <cprecord@editra.org>"
__svnid__ = "$Id: ed_style.py 54467 2008-07-02 19:51:00Z CJP $"
__revision__ = "$Revision: 54467 $"

#--------------------------------------------------------------------------#
# Dependancies
import os
import re
import wx
import util
from profiler import Profile_Get, Profile_Set

# Globals
STY_ATTRIBUTES     = u"face fore back size"
STY_EX_ATTRIBUTES  = u"eol bold italic underline"

# Parser Values
RE_ESS_COMMENT = re.compile("\/\*[^*]*\*+([^/][^*]*\*+)*\/")
RE_ESS_SCALAR = re.compile("\%\([a-zA-Z0-9]+\)")
RE_HEX_STR = re.compile("#[0-9a-fA-F]{3,6}")

#--------------------------------------------------------------------------#

class StyleItem(object):
    """A storage class for holding styling information
    @todo: The extra Attributes should be saved as a separate attribute in the
           StyleItem. This currenlty causes problems when customizing values in
           the StyleEditor. Changing this is fairly easy in this class but it
           will require changes to the StyleMgr and Editor as well.

    """
    def __init__(self, fore=wx.EmptyString, back=wx.EmptyString,
                       face=wx.EmptyString, size=wx.EmptyString):
        """Initiliazes the Style Object.

        @keyword fore: Specifies the forground color (hex string)
        @keyword face: Specifies the font face (string face name)
        @keyword back: Specifies the background color (hex string)
        @keyword size: Specifies font point size (int/formatted string)

        SPECIFICATION:
          - DATA FORMATS:
            - #123456       = hex color code
            - #123456,bold  = hex color code + extra style
            - Monaco        = Font Face Name
            - %(primary)s   = Format string to be swapped at runtime
            - 10            = A font point size
            - %(size)s      = Format string to be swapped at runtime
        """
        object.__init__(self)
        self.null = False
        self.fore = fore        # Foreground color hex code
        self.face = face        # Font face name
        self.back = back        # Background color hex code
        self.size = size        # Font point size

    def __eq__(self, si2):
        """Defines the == operator for the StyleItem Class
        @param si2: style item to compare to
        @return: whether the two items are equal
        @rtype: bool

        """
        return str(self) == str(si2)

    def __str__(self):
        """Converts StyleItem to a string
        @note: this return string is in a format that can be accepted by
               Scintilla. No spaces may be in the string after the ':'.
        @return: string representation of the StyleItem

        """
        style_str = wx.EmptyString
        if self.fore:
            style_str = u"fore:%s," % self.fore
        if self.back:
            style_str += u"back:%s," % self.back
        if self.face:
            style_str += u"face:%s," % self.face
        if self.size:
            style_str += u"size:%s," % str(self.size)

        if len(style_str) and style_str[-1] == u',':
            style_str = style_str[0:-1]
        return style_str

    #---- Get Functions ----#
    def GetAsList(self):
        """Returns a list of attr:value strings
        this style item.
        @return: list attribute values usable for building stc or ess values

        """
        retval = list()
        for attr in ('fore', 'back', 'face', 'size'):
            val = getattr(self, attr, None)
            if val not in ( None, wx.EmptyString ):
                retval.append(attr + ':' + val)
        return retval

    def GetBack(self):
        """Returns the value of the back attribute
        @return: style items background attribute

        """
        return self.back.split(',')[0]

    def GetFace(self):
        """Returns the value of the face attribute
        @return: style items font face attribute

        """
        return self.face.split(',')[0]

    def GetFore(self):
        """Returns the value of the fore attribute
        @return: style items foreground attribute

        """
        return self.fore.split(',')[0]

    def GetSize(self):
        """Returns the value of the size attribute as a string
        @return: style items font size attribute

        """
        return self.size.split(',')[0]

    def GetNamedAttr(self, attr):
        """Get the value of the named attribute
        @param attr: named attribute to get value of

        """
        return getattr(self, attr, None)

    #---- Utilities ----#
    def IsNull(self):
        """Return whether the item is null or not
        @return: bool

        """
        return self.null

    def IsOk(self):
        """Check if the style item is ok or not, if it has any of its
        attributes set it is percieved as ok.
        @return: bool

        """
        return len(self.__str__())

    def Nullify(self):
        """Clear all values and set item as Null
        @postcondition: item is turned into a NullStyleItem

        """
        self.null = True
        for attr in ('fore', 'face', 'back', 'size'):
            setattr(self, attr, '')

    #---- Set Functions ----#
    def SetAttrFromStr(self, style_str):
        """Takes style string and sets the objects attributes
        by parsing the string for the values. Only sets or
        overwrites values does not zero out previously set values.
        Returning True if value(s) are set or false otherwise.
        @param style_str: style information string (i.e fore:#888444)
        @type style_str: string

        """
        self.null = False
        last_set = wx.EmptyString
        for atom in style_str.split(u','):
            attrib = atom.split(u':')
            if len(attrib) == 2 and attrib[0] in STY_ATTRIBUTES:
                last_set = attrib[0]
                setattr(self, attrib[0], attrib[1])
            elif attrib[0] in STY_EX_ATTRIBUTES and last_set != wx.EmptyString:
                l_val = getattr(self, last_set)
                setattr(self, last_set, u",".join([l_val, attrib[0]]))
            else:
                pass

        return last_set != wx.EmptyString

    def SetBack(self, back, ex=wx.EmptyString):
        """Sets the Background Value
        @param back: hex color string, or None to clear attribute
        @keyword ex: extra attribute (i.e bold, italic, underline)

        """
        self.null = False
        if back is None or ex == wx.EmptyString:
            self.back = back
        else:
            self.back = u"%s,%s" % (back, ex)

    def SetFace(self, face, ex=wx.EmptyString):
        """Sets the Face Value
        @param face: font name string, or None to clear attribute
        @keyword ex: extra attribute (i.e bold, italic, underline)

        """
        if face is None or ex == wx.EmptyString:
            self.face = face
        else:
            self.face = u"%s,%s" % (face, ex)

    def SetFore(self, fore, ex=wx.EmptyString):
        """Sets the Foreground Value
        @param fore: hex color string, or None to clear attribute
        @keyword ex: extra attribute (i.e bold, italic, underline)

        """
        self.null = False
        if fore is None or ex == wx.EmptyString:
            self.fore = fore
        else:
            self.fore = u"%s,%s" % (fore, ex)

    def SetSize(self, size, ex=wx.EmptyString):
        """Sets the Font Size Value
        @param size: font point size, or None to clear attribute
        @type size: string or int
        @keyword ex: extra attribute (i.e bold, italic, underline)

        """
        self.null = False
        if size is None or ex == wx.EmptyString:
            self.size = size
        else:
            self.size = u"%s,%s" % (str(size), ex)

    def SetExAttr(self, ex_attr, add=True):
        """Adds an extra text attribute to a StyleItem. Currently
        (bold, eol, italic, underline) are supported. If the optional
        add value is set to False the attribute will be removed from
        the StyleItem.
        @param ex_attr: extra style attribute (bold, eol, italic, underline)
        @type ex_attr: string
        @keyword add: Add a style (True) or remove a style (False)

        """
        # Get currently set attributes
        self.null = False
        cur_str = self.__str__()
        if not add:
            cur_str = cur_str.replace(u',' + ex_attr, wx.EmptyString)
            self.SetAttrFromStr(cur_str)
        else:
            if u',' + ex_attr not in cur_str:
                attr_map = { u"fore" : self.GetFore(),
                             u"back" : self.GetBack(),
                             u"face" : self.GetFace(),
                             u"size" : self.GetSize()
                           }
                for key in attr_map:
                    if len(attr_map[key]) and u"," not in attr_map[key]:
                        setattr(self, key, u",".join([attr_map[key], ex_attr]))
                        break
            else:
                pass

    def SetNamedAttr(self, attr, value):
        """Sets a StyleItem attribute by named string.
        @note: This is not intended to be used for setting extra
               attributes such as bold, eol, ect..
        @param attr: a particular attribute to set (i.e fore, face, back, size)
        @param value: value to set the attribute to contain

        """
        self.null = False
        cur_val = getattr(self, attr, None)
        if cur_val is not None:
            if u"," in cur_val:
                tmp = cur_val.split(u",")
                tmp[0] = value
                value = u",".join(tmp)
        setattr(self, attr, value)

#-----------------------------------------------------------------------------#

class StyleMgr(object):
    """Manages style definitions and provides them on request.
    Also provides functionality for loading custom style sheets and
    modifying styles during run time.

    """
    STYLES         = dict()         # Cache for loaded style set(s)
    FONT_PRIMARY   = u"primary"
    FONT_SECONDARY = u"secondary"
    FONT_SIZE      = u"size"
    FONT_SIZE2     = u"size2"
    FONT_SIZE3     = u"size3"

    def __init__(self, custom=wx.EmptyString):
        """Initializes the Style Manager
        @keyword custom: path to custom style sheet to use

        """
        object.__init__(self)

        # Attributes
        self.fonts = self.GetFontDictionary()
        self.style_set = custom
        self.LOG = wx.GetApp().GetLog()

        # Get the Style Set
        if custom != wx.EmptyString and self.LoadStyleSheet(custom):
            self.LOG("[ed_style][info] Loaded custom style sheet %s" % custom)
        else:
            self.LOG("[ed_style][err] Failed to import styles from %s" % custom)

    def BlankStyleDictionary(self):
        """Returns a dictionary of unset style items based on the
        tags defined in the current dictionary.
        @return: dictionary of unset style items using the current tag set
                 as keys.

        """
        sty_dict = dict()
        for key in self.GetStyleSet().keys():
            if key in ('select_style', 'whitespace_style'):
                sty_dict[key] = NullStyleItem()
            else:
                sty_dict[key] = StyleItem("#000000", "#FFFFFF",
                                          "%(primary)s", "%(size)d")
        return sty_dict

    def GetFontDictionary(self, default=True):
        """Does a system lookup to build a default set of fonts using
        ten point fonts as the standard size.
        @keyword default: return the default dictionary of fonts, else return
                          the current running dictionary of fonts if it exists.
        @type default: bool
        @return: font dictionary (primary, secondary) + (size, size2)

        """
        if hasattr(self, 'fonts') and not default:
            return self.fonts

        font = Profile_Get('FONT1', 'font', None)
        if font is not None:
            mfont = font
        else:
            mfont = wx.Font(10, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL,
                            wx.FONTWEIGHT_NORMAL)
            Profile_Set('FONT1', mfont, 'font')
        primary = mfont.GetFaceName()

        font = Profile_Get('FONT2', 'font', None)
        if font is None:
            font = wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL,
                            wx.FONTWEIGHT_NORMAL)
            Profile_Set('FONT2', font, 'font')
        secondary = font.GetFaceName()
        faces = {
                  self.FONT_PRIMARY   : primary,
                  self.FONT_SECONDARY : secondary,
                  self.FONT_SIZE  : mfont.GetPointSize(),
                  self.FONT_SIZE2 : font.GetPointSize(),
                  self.FONT_SIZE3 : mfont.GetPointSize() - 2
                 }
        return faces

    def GetDefaultFont(self):
        """Constructs and returns a wxFont object from the settings
        of the default_style object.
        @return: font object of default style
        @rtype: wx.Font

        """
        if self.HasNamedStyle('default_style'):
            style_item = self.GetItemByName('default_style')
            face = style_item.GetFace()
            if face[0] == u"%":
                face = face % self.fonts
            size = style_item.GetSize()
            if isinstance(size, basestring):
                size = size % self.fonts
            font = wx.FFont(int(size), wx.MODERN, face=face)
        else:
            font = wx.FFont(self.fonts[self.FONT_SIZE], wx.MODERN)
        return font

    def GetDefaultForeColour(self, as_hex=False):
        """Gets the foreground color of the default style and returns
        a Colour object. Otherwise returns Black if the default
        style is not found.
        @keyword as_hex: return a hex string or colour object
        @type as_hex: bool
        @return: wx.Colour of default style foreground or hex value
        @rtype: wx.Colour or string

        """
        fore = self.GetItemByName('default_style').GetFore()
        if fore == wx.EmptyString:
            fore = u"#000000"

        if not as_hex:
            rgb = util.HexToRGB(fore[1:])
            fore = wx.Colour(red=rgb[0], green=rgb[1], blue=rgb[2])
        return fore

    def GetDefaultBackColour(self, as_hex=False):
        """Gets the background color of the default style and returns
        a Colour object. Otherwise returns white if the default
        style is not found.
        @keyword hex: return a hex string or colour object
        @type hex: bool
        @return: wx.Colour of default style background or hex value
        @rtype: wx.Colour or string

        """
        back = self.GetItemByName('default_style').GetBack()
        if back == wx.EmptyString:
            back = u"#FFFFFF"

        if not as_hex:
            rgb = util.HexToRGB(back[1:])
            back = wx.Colour(red=rgb[0], green=rgb[1], blue=rgb[2])
        return back

    def GetItemByName(self, name):
        """Gets and returns a style item using its name for the search
        @param name: tag name of style item to get
        @return: style item (may be empty/null style item)
        @rtype: L{StyleItem}

        """
        if self.HasNamedStyle(name):
            if u"%" in unicode(StyleMgr.STYLES[self.style_set][name]):
                val = unicode(StyleMgr.STYLES[self.style_set][name]) % self.fonts
                item = StyleItem()
                item.SetAttrFromStr(val)
                return item
            else:
                return StyleMgr.STYLES[self.style_set][name]
        else:
            return StyleItem()

    def GetStyleFont(self, primary=True):
        """Returns the primary font facename by default
        @keyword primary: Get Primary(default) or Secondary Font
        @return face name of current font in use

        """
        if primary:
            font = wx.FFont(self.fonts[self.FONT_SIZE], wx.DEFAULT,
                            face=self.fonts[self.FONT_PRIMARY])
        else:
            font = wx.FFont(self.fonts[self.FONT_SIZE2], wx.DEFAULT,
                            face=self.fonts[self.FONT_SECONDARY])
        return font

    def GetStyleByName(self, name):
        """Gets and returns a style string using its name for the search
        @param name: tag name of style to get
        @type name: string
        @return: style item in string form
        @rtype: string

        """
        if self.HasNamedStyle(name):
            return unicode(self.GetItemByName(name))
        else:
            return wx.EmptyString

    def GetStyleSet(self):
        """Returns the current set of styles or the default set if
        there is no current set.
        @return: current style set dictionary
        @rtype: dict

        """
        return StyleMgr.STYLES.get(self.style_set, DefaultStyleDictionary())

    def HasNamedStyle(self, name):
        """Checks if a style has been set/loaded or not
        @param name: tag name of style to look for
        @return: whether item is in style set or not

        """
        return self.GetStyleSet().has_key(name)

    def LoadStyleSheet(self, style_sheet, force=False):
        """Loads a custom style sheet and returns True on success
        @param style_sheet: path to style sheet to load
        @keyword force: Force reparse of style sheet, default is to use cached
                        data when available
        @return: whether style sheet was loaded or not
        @rtype: bool

        """
        if isinstance(style_sheet, basestring) and \
           os.path.exists(style_sheet) and \
           ((force or not StyleMgr.STYLES.has_key(style_sheet)) or \
             style_sheet != self.style_set):
            reader = util.GetFileReader(style_sheet)
            if reader == -1:
                self.LOG("[ed_style][err] Failed to open style sheet: %s" % style_sheet)
                return False
            ret_val = self.SetStyles(style_sheet, self.ParseStyleData(reader.read()))
            reader.close()
            return ret_val
        elif not StyleMgr.STYLES.has_key(style_sheet):
            self.LOG("[ed_style][warn] Style sheet %s does not exists" % style_sheet)
            self.SetStyles('default', DefaultStyleDictionary())
            return False
        else:
            self.LOG("[ed_style][info] Using cached style data")
            return True

    def PackStyleSet(self, style_set):
        """Checks the difference of each item in the style set as
        compared to the default_style tag and packs any unset value
        in the item to be equal to the default style.
        @param style_set: style set to pack
        @return: style_set with all unset attributes set to match default style

        """
        if isinstance(style_set, dict) and style_set.has_key('default_style'):
            default = style_set['default_style']
            for tag in style_set:
                if style_set[tag].IsNull():
                    continue
                if style_set[tag].GetFace() == wx.EmptyString:
                    style_set[tag].SetFace(default.GetFace())
                if style_set[tag].GetFore() == wx.EmptyString:
                    style_set[tag].SetFore(default.GetFore())
                if style_set[tag].GetBack() == wx.EmptyString:
                    style_set[tag].SetBack(default.GetBack())
                if style_set[tag].GetSize() == wx.EmptyString:
                    style_set[tag].SetSize(default.GetSize())
        else:
            pass
        return style_set

    def ParseStyleData(self, style_data, strict=False):
        """Parses a string style definitions read from an Editra
        Style Sheet. If the parameter 'strict' isnt set then any
        syntax errors are ignored and only good values are returned.
        If 'strict' is set the parser will raise errors and bailout.
        @param style_data: style sheet data string
        @type style_data: string
        @keyword strict: should the parser raise errors or ignore
        @return: dictionary of StyleItems constructed from the style sheet
                 data.

        """
        # Remove all comments
        style_data = RE_ESS_COMMENT.sub(u'', style_data)

        # Compact data into a contiguous string
        style_data = style_data.replace(u"\r\n", u"").replace(u"\n", u"")
        style_data = style_data.replace(u"\t", u"")

        ## Build style data tree
        # Tree Level 1 split tag from data
        style_tree = [style.split(u"{") for style in style_data.split(u'}')]
        if len(style_tree) and style_tree[-1][0] == wx.EmptyString:
            style_tree.pop()

        # Check for Level 1 Syntax Errors
        tmp = style_tree
        for style in tmp:
            if len(style) != 2:
                self.LOG("[ed_style][err] There was an error parsing "
                         "the syntax data from " + self.style_set)
                self.LOG("[ed_style][err] You are missing a { or } " +
                         "in Def: " + style[0].split()[0])
                if strict:
                    raise SyntaxError, \
                          "Missing { or } near Def: %s" % style[0].split()[0]
                else:
                    style_tree.remove(style)

        # Tree Level 2 Build small trees of tag and style attributes
        # Tree Level 3 Branch tree into TAG => Attr => Value String
        for branch in style_tree:
            tmp2 = [leaf.strip().split(u":")
                    for leaf in branch[1].strip().split(u";")]
            if len(tmp2) and tmp2[-1][0] == wx.EmptyString:
                tmp2.pop()
            branch[1] = tmp2

        # Check for L2/L3 Syntax errors and build a clean dictionary
        # of Tags => Valid Attributes
        style_dict = dict()
        for branch in style_tree:
            value = list()
            tag = branch[0].replace(u" ", u"")
            for leaf in branch[1]:
                # Remove any remaining whitespace
                leaf = [part.strip() for part in leaf]
                if len(leaf) != 2:
                    self.LOG("[ed_style][err] Missing a : or ; in the "
                             "declaration of %s" % tag)
                    if strict:
                        raise SyntaxError, "Missing : or ; in def: %s" % tag
                elif leaf[0] not in STY_ATTRIBUTES:
                    self.LOG(("[ed_style][warn] Unknown style attribute: %s"
                             ", In declaration of %s") % (leaf[0], tag))
                    if strict:
                        raise SyntaxWarning, "Unknown attribute %s" % leaf[0]
                else:
                    value.append(leaf)
            style_dict[tag] = value

        # Trim the leafless branches from the dictionary
        tmp = style_dict.copy()
        for style_def in tmp:
            if len(tmp[style_def]) == 0:
                style_dict.pop(style_def)

        # Validate leaf values and format into style string
        for style_def in style_dict:
            if not style_def[0][0].isalpha():
                self.LOG("[ed_style][err] The style def %s is not a "
                         "valid name" % style_def[0])
                if strict:
                    raise SyntaxError, "%s is an invalid name" % style_def[0]
            else:
                style_str = wx.EmptyString
                for attrib in style_dict[style_def]:
                    values = [ val for val in attrib[1].split(u" ")
                               if val != wx.EmptyString ]
                    if len(values) > 2:
                        self.LOG("[ed_style][warn] Only one extra " +
                                 "attribute can be set per style. See " +
                                 style_def + " => " + attrib[0])
                        if strict:
                            raise SyntaxWarning

                    # Validate values
                    v1ok = v2ok = False
                    if attrib[0] in "fore back" and RE_HEX_STR.match(values[0]):
                        v1ok = True
                    elif len(values) and attrib[0] == "size":
                        if RE_ESS_SCALAR.match(values[0]) or values[0].isdigit():
                            v1ok = True
                        else:
                            self.LOG("[ed_style][warn] Bad value in %s"
                                     " the value %s is invalid." % \
                                     (attrib[0], values[0]))
                    elif len(values) and attrib[0] == "face":
                        if len(values) == 2 and \
                           values[1] not in STY_EX_ATTRIBUTES:
                            values = [u' '.join(values)]
                        v1ok = True

                    if len(values) == 2 and values[1] in STY_EX_ATTRIBUTES:
                        v2ok = True
                    elif len(values) == 2:
                        self.LOG("[ed_style][warn] Unknown extra " + \
                                 "attribute '" + values[1] + \
                                 "' in attribute: " + attrib[0])

                    if v1ok and v2ok:
                        value = u",".join(values)
                    elif v1ok:
                        value = values[0]
                    else:
                        continue

                    style_str = u",".join([style_str,
                                           u":".join([attrib[0], value])])

                if style_str != wx.EmptyString:
                    style_dict[style_def] = style_str.strip(u",")

        # Build a StyleItem Dictionary
        for key, value in style_dict.iteritems():
            new_item = StyleItem()
            if isinstance(value, basestring):
                new_item.SetAttrFromStr(value)
            style_dict[key] = new_item

        # For any undefined tags load them as empty items
        for key in DefaultStyleDictionary().keys():
            if key not in style_dict:
                style_dict[key] = StyleItem()

        return style_dict

    def SetGlobalFont(self, font_tag, fontface, size=-1):
        """Sets one of the fonts in the global font set by tag
        and sets it to the named font. Returns true on success.
        @param font_tag: fonttype identifier key
        @param fontface: face name to set global font to

        """
        if hasattr(self, 'fonts'):
            self.fonts[font_tag] = fontface
            if size > 0:
                self.fonts[self.FONT_SIZE] = size
            return True
        else:
            return False

    def SetStyleFont(self, wx_font, primary=True):
        """Sets the\primary or secondary font and their respective
        size values.
        @param wx_font: font object to set styles font info from
        @keyword primary: Set primary(default) or secondary font

        """
        if primary:
            self.fonts[self.FONT_PRIMARY] = wx_font.GetFaceName()
            self.fonts[self.FONT_SIZE] = wx_font.GetPointSize()
        else:
            self.fonts[self.FONT_SECONDARY] = wx_font.GetFaceName()
            self.fonts[self.FONT_SIZE2] = wx_font.GetPointSize()

    def SetStyleTag(self, style_tag, value):
        """Sets the value of style tag by name
        @param style_tag: desired tag name of style definition
        @param value: style item to set tag to

        """
        StyleMgr.STYLES[self.style_set][style_tag] = value

    def SetStyles(self, name, style_dict, nomerge=False):
        """Sets the managers style data and returns True on success.
        @param name: name to store dictionary in cache under
        @param style_dict: dictionary of style items to use as managers style
                           set.
        @keyword nomerge: merge against default set or not
        @type nomerge: bool

        """
        if nomerge:
            self.style_set = name
            StyleMgr.STYLES[name] = self.PackStyleSet(style_dict)
            return True

        # Merge the given style set with the default set to fill in any
        # unset attributes/tags
        if isinstance(style_dict, dict):
            # Check for bad data
            for style in style_dict.values():
                if not isinstance(style, StyleItem):
                    self.LOG("[ed_style][err] Invalid data in style dictionary")
                    return False

            self.style_set = name
            # Set any undefined styles to match the default_style
            for tag, item in DefaultStyleDictionary().iteritems():
                if tag not in style_dict:
                    if tag in ['select_style', 'whitespace_style']:
                        style_dict[tag] = NullStyleItem()
                    elif tag in ['foldmargin_style']:
                        style_dict[tag] = style_dict['default_style']
                    else:
                        style_dict[tag] = item

            StyleMgr.STYLES[name] = self.PackStyleSet(style_dict)
            return True
        else:
            self.LOG("[ed_style][err] SetStyles expects a " \
                     "dictionary of StyleItems")
            return False

#-----------------------------------------------------------------------------#
# Utility Functions
def DefaultStyleDictionary():
    """This is the default style values that are used for styling
    documents. Its used as a fallback for undefined values in a
    style sheet.
    @note: incomplete style sheets are merged against this set to ensure
           a full set of definitions is avaiable

    """
    def_dict = \
        {'brace_good' : StyleItem("#FFFFFF", "#0000FF,bold"),
         'brace_bad'  : StyleItem(back="#FF0000,bold"),
         'calltip'    : StyleItem("#404040", "#FFFFB8"),
         'caret_line' : StyleItem(back="#D8F8FF"),
         'ctrl_char'  : StyleItem(),
         'line_num'   : StyleItem(back="#C0C0C0", face="%(secondary)s", \
                                  size="%(size3)d"),
         'array_style': StyleItem("#EE8B02,bold", face="%(secondary)s"),
         'btick_style': StyleItem("#8959F6,bold", size="%(size)d"),
         'default_style': StyleItem("#000000", "#F6F6F6", \
                                    "%(primary)s", "%(size)d"),
         'char_style' : StyleItem("#FF3AFF"),
         'class_style' : StyleItem("#2E8B57,bold"),
         'class2_style' : StyleItem("#2E8B57,bold"),
         'comment_style' : StyleItem("#838383"),
         'decor_style' : StyleItem("#BA0EEA italic", face="%(secondary)s"),
         'directive_style' : StyleItem("#0000FF,bold", face="%(secondary)s"),
         'dockey_style' : StyleItem("#0000FF"),
         'error_style' : StyleItem("#DD0101,bold", face="%(secondary)s"),
         'foldmargin_style' : StyleItem(back="#D1D1D1"),
         'funct_style' : StyleItem("#008B8B,italic"),
         'global_style' : StyleItem("#007F7F,bold", face="%(secondary)s"),
         'guide_style' : StyleItem("#838383"),
         'here_style' : StyleItem("#CA61CA,bold", face="%(secondary)s"),
         'ideol_style' : StyleItem("#E0C0E0", face="%(secondary)s"),
         'keyword_style' : StyleItem("#A52B2B,bold"),
         'keyword2_style' : StyleItem("#2E8B57,bold"),
         'keyword3_style' : StyleItem("#008B8B,bold"),
         'keyword4_style' : StyleItem("#9D2424"),
         'marker_style' : StyleItem("#FFFFFF", "#000000"),
         'number_style' : StyleItem("#DD0101"),
         'number2_style' : StyleItem("#DD0101,bold"),
         'operator_style' : StyleItem("#000000", face="%(primary)s,bold"),
         'pre_style' : StyleItem("#AB39F2,bold"),
         'pre2_style' : StyleItem("#AB39F2,bold", "#FFFFFF"),
         'regex_style' : StyleItem("#008B8B"),
         'scalar_style' : StyleItem("#AB37F2,bold", face="%(secondary)s"),
         'scalar2_style' : StyleItem("#AB37F2", face="%(secondary)s"),
         'select_style' : NullStyleItem(), # Use system default colour
         'string_style' : StyleItem("#FF3AFF,bold"),
         'stringeol_style' : StyleItem("#000000,bold", "#EEC0EE,eol", \
                                       "%(secondary)s"),
         'unknown_style' : StyleItem("#FFFFFF,bold", "#DD0101,eol"),
         'whitespace_style' : StyleItem('#838383')
         }
    return def_dict

def MergeFonts(style_dict, font_dict):
    """Does any string substitution that the style dictionary
    may need to have fonts and their sizes set.
    @param style_dict: dictionary of L{StyleItem}
    @param font_dict: dictionary of font data
    @return: style dictionary with all font format strings substituded in

    """
    for style in style_dict:
        st_str = str(style_dict[style])
        if u'%' in st_str:
            style_dict[style].SetAttrFromStr(st_str % font_dict)
    return style_dict

def MergeStyles(styles1, styles2):
    """Merges the styles from styles2 into styles1 overwriting
    any duplicate values already set in styles1 with the new
    data from styles2.
    @param styles1: dictionary of StyleItems recieve merge
    @param styles2: dictionary of StyleItems to merge from
    @return: style1 with all values from styles2 merged into it

    """
    for style in styles2:
        styles1[style] = styles2[style]
    return styles1

def NullStyleItem():
    """Create a null style item
    @return: empty style item that cannot be merged

    """
    item = StyleItem()
    item.null = True
    return item
