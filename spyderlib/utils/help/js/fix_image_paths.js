//----------------------------------------------------------------------------
//  Set absolute path for images
//
//  Copyright 2014 by The Spyder development team
//
//  Distributed under the terms of the MIT License
//----------------------------------------------------------------------------

//============================================================================
// On document ready
//============================================================================

$(document).ready(function () {
    $('img').attr('src', function(index, attr){
        var path = attr.split('/')
        var img_name = path.reverse()[0]
        return '{{img_path}}' + '/' + img_name
    });
});
