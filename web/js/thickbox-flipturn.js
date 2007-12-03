/*
 * Thickbox 1.1 - One box to rule them all.
 * By Cody Lindley (http://www.codylindley.com)
 * Under an Attribution, Share Alike License
 * Thickbox is built on top of the very light weight jquery library.
 */

//on page load call TB_init
$(document).ready(TB_init);

var border=5;
var vspacer=10;
var hspacer=10;
var TB_PrevCaption, TB_PrevURL, TB_NextCaption, TB_NextURL;

//add thickbox to href elements that have a class of .thickbox
function TB_init(){
	$("a.thickbox").click(function(){
		var t = this.title || this.innerHTML || this.href;
		TB_show(t,this.href);
		this.blur();
		return false;
	});
}

function TB_show(caption, url) {//function called when the user clicks on a thickbox link
	try {
		if (document.getElementById("TB_overlay") == null) {
			$("body").append("<div id='TB_overlay'></div><div id='TB_window'></div>");
			$("#TB_overlay").click(TB_remove);
		}
		$(window).resize(TB_position);
		$(window).scroll(TB_position);
 		
		$("#TB_overlay").show();
		$("body").append("<div id='TB_load'><div id='TB_loadContent'><img src='/images/circle_animation.gif' /></div></div>");
		
	
		var urlString = /\.jpg|\.jpeg|\.png|\.gif|\.html|\.htm|\.php|\.cfm|\.asp|\.aspx|\.jsp|\.jst|\.rb|\.txt/g;
		var urlType = url.toLowerCase().match(urlString);
		
		if(urlType == '.jpg' || urlType == '.jpeg' || urlType == '.png' || urlType == '.gif'){//code to show images
			TB_PrevCaption = "";
			TB_PrevURL = "";
			TB_PrevHTML = "";
			TB_PrevRel = "";
			TB_Rel = "";
			TB_NextCaption = "";
			TB_NextURL = "";
			TB_NextHTML = "";
			TB_NextRel = "";
            TB_CaptionID = "";
            TB_Printable = "";
			TB_FoundURL = false;
			TB_TempArray = $("a.thickbox").get();
			for (TB_Counter = 0; ((TB_Counter < TB_TempArray.length) && (TB_NextHTML == "")); TB_Counter++) {
				var urlTypeTemp = TB_TempArray[TB_Counter].href.toLowerCase().match(urlString);
				if(urlTypeTemp == '.jpg' || urlTypeTemp == '.jpeg' || urlTypeTemp == '.png' || urlTypeTemp == '.gif'){//code is an image
					if (!(TB_TempArray[TB_Counter].href == url)) {
						if (TB_FoundURL) {
							if (TB_Rel == TB_TempArray[TB_Counter].rel) {
								TB_NextCaption = TB_TempArray[TB_Counter].title;
								TB_NextURL = TB_TempArray[TB_Counter].href;
								TB_NextHTML = "<div id='TB_next'><a href='#'>Next &gt;&gt;</a></div>";
								TB_NextRel = TB_TempArray[TB_Counter].rel;
							}
						} else {
							TB_PrevCaption = TB_TempArray[TB_Counter].title;
							TB_PrevURL = TB_TempArray[TB_Counter].href;
							TB_PrevHTML = "<div id='TB_prev'><a href='#'>&lt;&lt; Prev</a></div>";
							TB_PrevRel = TB_TempArray[TB_Counter].rel;
						}
					} else {
						TB_FoundURL = true;
						TB_Rel = TB_TempArray[TB_Counter].rel;
                        TB_CaptionID = TB_TempArray[TB_Counter].id;
                        p = TB_TempArray[TB_Counter].name;
                        if (!(p == "")) {
                            TB_Printable = "<a href='" + p +"' target='_blank'>full-size</a>";
                        }
                        else {
                            TB_Printable = "";
                        }
                        
						if (!(TB_PrevURL == "")) {
							if (!(TB_Rel == TB_PrevRel)) {
								// Previous image was in a different group, remove it.
								TB_PrevCaption = "";
								TB_PrevURL = "";
								TB_PrevHTML = "";
								TB_PrevRel = "";
							}
						}
					}
				}
			}
			var imgPreloader = new Image();
			imgPreloader.onload = function(){
				
			// Resizing large images added by Christian Montoya
			var pagesize = getPageSize();
			var x = pagesize[0] - border - 2*hspacer;
			var y = pagesize[1] - border - 2*vspacer;
			var imageWidth = imgPreloader.width;
			var imageHeight = imgPreloader.height;
			if (imageWidth > x) {
				imageHeight = imageHeight * (x / imageWidth); 
				imageWidth = x; 
				if (imageHeight > y) { 
					imageWidth = imageWidth * (y / imageHeight); 
					imageHeight = y; 
				}
			} else if (imageHeight > y) { 
				imageWidth = imageWidth * (y / imageHeight); 
				imageHeight = y; 
				if (imageWidth > x) { 
					imageHeight = imageHeight * (x / imageWidth); 
					imageWidth = x;
				}
			}
			// End Resizing
			
			
			TB_WIDTH = imageWidth + hspacer;
			TB_HEIGHT = imageHeight + vspacer;
			$("#TB_window").append("<div id='TB_caption'>"+caption+"</div><div id='TB_closeWindow'>" + TB_Printable + " <a href='#' id='TB_closeWindowButton'>close</a></div><div id='TB_SecondLine'>" + TB_PrevHTML + TB_NextHTML + "</div><div id='TB_ImageDIV'><a href='' id='TB_ImageOff' title='Close'><img id='TB_Image' src='"+url+"' width='"+imageWidth+"' height='"+imageHeight+"' alt='"+caption+"'/></a></div>");
			$("#TB_closeWindowButton").click(TB_remove);
			if (!(TB_PrevHTML == "")) {
				$("#TB_prev").click(function () {
					$("#TB_window").slideUp("slow");
					$("#TB_load").remove();
					$("#TB_window").remove();
					$("body").append("<div id='TB_window'></div>");
					TB_show(TB_PrevCaption, TB_PrevURL);
				});
			}
			if (!(TB_NextHTML == "")) {
				$("#TB_next").click(function () {
					$("#TB_window").slideUp("slow");
					$("#TB_load").remove();
					$("#TB_window").remove();
					$("body").append("<div id='TB_window'></div>");
					TB_show(TB_NextCaption, TB_NextURL);
				});
			}
              //$("#TB_caption").editable("caption.cgi", { saving:"<img src='/images/indicator.gif'>", size:80, extraParams:{id:TB_CaptionID} });
			TB_position();
			$("#TB_load").remove();
			$("#TB_ImageOff").click(TB_remove);
			$("#TB_window").slideDown("normal");
			}
	  
			imgPreloader.src = url;
		}
		
		if(urlType=='.htm'||urlType=='.html'||urlType=='.php'||urlType=='.asp'||urlType=='.aspx'||urlType=='.jsp'||urlType=='.jst'||urlType=='.rb'||urlType=='.txt'||urlType=='.cfm'){//code to show html pages
			
			var queryString = url.replace(/^[^\?]+\??/,'');
			var params = parseQuery( queryString );
			
			TB_WIDTH = (params['width']*1) + 30;
			TB_HEIGHT = (params['height']*1) + 40;
			ajaxContentW = TB_WIDTH - 30;
			ajaxContentH = TB_HEIGHT - 45;
			$("#TB_window").append("<div id='TB_closeAjaxWindow'><a href='#' id='TB_closeWindowButton'>close</a></div><div id='TB_ajaxContent' style='width:"+ajaxContentW+"px;height:"+ajaxContentH+"px;'></div>");
			$("#TB_closeWindowButton").click(TB_remove);
			$("#TB_ajaxContent").load(url, function(){
			TB_position();
			$("#TB_load").remove();
			$("#TB_window").slideDown("normal");
			});
		}
		
	} catch(e) {
		alert( e );
	}
}

//helper functions below

function TB_remove() {
	$("#TB_window").fadeOut("fast",function(){$('#TB_window,#TB_overlay').remove();});
	$("#TB_load").remove();
	return false;
}

function TB_position() {
	var pagesize = getPageSize();
  
  	if (window.innerHeight && window.scrollMaxY) {	
		yScroll = window.innerHeight + window.scrollMaxY;
	} else if (document.body.scrollHeight > document.body.offsetHeight){ // all but Explorer Mac
		yScroll = document.body.scrollHeight;
	} else { // Explorer Mac...would also work in Explorer 6 Strict, Mozilla and Safari
		yScroll = document.body.offsetHeight;
  	}
	
	var arrayPageScroll = getPageScrollTop();
	
	$("#TB_window").css({width:TB_WIDTH+"px",height:TB_HEIGHT+"px",
	left: ((pagesize[0] - TB_WIDTH)/2)+"px", top: (arrayPageScroll[1] + ((pagesize[1]-TB_HEIGHT)/2))+"px" });
	$("#TB_overlay").css("height",yScroll +"px");

}

function parseQuery ( query ) {
   var Params = new Object ();
   if ( ! query ) return Params; // return empty object
   var Pairs = query.split(/[;&]/);
   for ( var i = 0; i < Pairs.length; i++ ) {
      var KeyVal = Pairs[i].split('=');
      if ( ! KeyVal || KeyVal.length != 2 ) continue;
      var key = unescape( KeyVal[0] );
      var val = unescape( KeyVal[1] );
      val = val.replace(/\+/g, ' ');
      Params[key] = val;
   }
   return Params;
}


function getPageScrollTop(){
	var yScrolltop;
	if (self.pageYOffset) {
		yScrolltop = self.pageYOffset;
	} else if (document.documentElement && document.documentElement.scrollTop){	 // Explorer 6 Strict
		yScrolltop = document.documentElement.scrollTop;
	} else if (document.body) {// all other Explorers
		yScrolltop = document.body.scrollTop;
	}
	arrayPageScroll = new Array('',yScrolltop) 
	return arrayPageScroll;
}

function getPageSize(){
	var de = document.documentElement;
	var w = window.innerWidth || self.innerWidth || (de&&de.clientWidth) || document.body.clientWidth;
	var h = window.innerHeight || self.innerHeight || (de&&de.clientHeight) || document.body.clientHeight;
	
	arrayPageSize = new Array(w,h) 
	return arrayPageSize;
}
