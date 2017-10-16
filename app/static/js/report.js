$(function() {
    $(document).ready(function(){

	var val2 = document.getElementById("val2");
	val2.innerHTML = "<div style='text-align:center; font-size: 250%;'><i class='fa fa-spinner fa-pulse fa-4x fa-fw'></i></div>";

	var msg = document.getElementById("msg");

	$.getJSON($SCRIPT_ROOT + '/_file2db', {
	    fn: $('input[name="fn"]').val()
	}, function(data) {

	    if (data.result) {
		r = String(data.result);
		msg.innerHTML = "";
		val2.innerHTML = r;
	    } else {
		val2.innerHTML = "We were unable to process your file.   We will do our best to fix this, but may not be able to.";
		swal('Something bad happened.',
		     'Please report this!',
		     'error');
	    }

	});




    });
});


