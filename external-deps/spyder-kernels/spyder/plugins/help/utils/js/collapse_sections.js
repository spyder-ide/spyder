//----------------------------------------------------------------------------
//  Toggleable sections
//
//  Copyright 2011-2012 by Assurance Technologies
//  Copyright 2014- Spyder Project Contributors
//
//  Distributed under the terms of the 3-Clause BSD License
//  (see NOTICE.txt in the Spyder repo's root directory for more details)
//
//----------------------------------------------------------------------------
//
//  Added expand/collapse functionality to RST sections.
//
//  Adapted from portions of cloud_sptheme/themes/cloud/static/cloud.js_t
//  from the Cloud Sphinx theme:
//  https://bitbucket.org/ecollins/cloud_sptheme/
//----------------------------------------------------------------------------

//============================================================================
// On document ready
//============================================================================

$(document).ready(function (){
  function init(){
    // get header & section, and add static classes
    var header = $(this);
    var section = header.parent();
    header.addClass("html-toggle-button");

    // helper to test if url hash is within this section
    function contains_hash(){
      var hash = document.location.hash;
      return hash && (section[0].id == hash.substr(1) ||
              section.find(hash.replace(/\./g,"\\.")).length>0);
    }

    // helper to control toggle state
    function set_state(expanded){
      if(expanded){
        section.addClass("expanded").removeClass("collapsed");
        section.children().show();
      }else{
        section.addClass("collapsed").removeClass("expanded");
        section.children().hide();
        section.children("span:first-child:empty").show(); /* for :ref: span tag */
        header.show();
      }
    }

    // initialize state
    set_state(section.hasClass("expanded") || contains_hash());

    // bind toggle callback
    header.click(function (){
      section.children().next().slideToggle(300);
      set_state(!section.hasClass("expanded"));
      $(window).trigger('cloud-section-toggled', section[0]);
    });

    // open section if user jumps to it from w/in page
    $(window).bind("hashchange", function () {
      if(contains_hash()) {
        var link = document.location.hash;
        $(link).parents().each(set_state, [true]);
        set_state(true);
        $('html, body').animate({ scrollTop: $(link).offset().top }, 'fast');
      }
    });
  }

  $(".section > h2, .section > h3, .section > h4").each(init);
});
