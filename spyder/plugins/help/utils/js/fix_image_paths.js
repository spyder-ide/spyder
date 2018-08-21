//----------------------------------------------------------------------------
//  Set absolute path for images
//
//  Copyright (c) Spyder Project Contributors
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
        return 'file:///{{img_path}}' + '/' + img_name
    });
});
