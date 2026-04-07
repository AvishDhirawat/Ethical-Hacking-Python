// Fullscreen
$(function () {
    'use strict'
  
    $('[data-provide~="fullscreen"]').on('click', function () {
      screenfull.toggle($('#container')[0]);
    });
  
  }); // End of use strict
  