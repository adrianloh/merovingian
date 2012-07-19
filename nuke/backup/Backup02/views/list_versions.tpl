<html xmlns="http://www.w3.org/1999/xhtml">
 <head>
 	<meta http-equiv="content-type" content="text/html; charset=utf-8" />
 	<title>{{title}}</title>
 	<link href="/static/default.css" rel="stylesheet" type="text/css" />
 	<script type="text/javascript">
		function popup(url) {
    		window.open(url,"Homepage","resizable=no,status=no,scrollbars=no,width=500,height=300");
		}
 	</script>
 	</head>
 <body>
 	<div id="header">
 		<h1>{{title}}</h1>
 	</div>
 	<div id="page">
  %for item in items:
  	<ul>
  		<h1 class="title">{{item.title}}</h1>
  		<div class="post">
  			<div class="meta">
			<p class="date">{{item.versionMajor}}.{{item.versionMinor}} | {{item.modified}} | {{item.status}}</p>
    		</div>
		<li> <a href={{"javascript:popup(\"/edit/%i\")"%item.id}}>Edit</a> | <a href={{"javascript:popup(\"/render/%i\")"%item.id}}>Render</a></li>
		</div>
    </ul>
  %end
    </div>
 </body>
</html>