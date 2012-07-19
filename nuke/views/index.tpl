<html>
<head>
  <style>img{ height: 100px; float: left; }</style>
  <script src="static/jquery1.4.1.js"></script>
  <script>
  		$(document).ready(function(){
		$.getJSON("http://127.0.0.1/getjson",function(data){
			$.each(data.items, function(i,item){
				console.log(item)
			});
		});
	});
  </script>
</head>
<body>
fdsfds
</body>
</html>