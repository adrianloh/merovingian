<html xmlns="http://www.w3.org/1999/xhtml">
 <head>
 	<meta http-equiv="content-type" content="text/html; charset=utf-8" />
 	<title>{{title}}</title>
 	<link href="/static/default.css" rel="stylesheet" type="text/css" />
 </head>
 <body>
 	<div id="header">
 		<h1>{{title}}</h1>
 	</div>
 	<div id="page">
  %for item in items:
  	<ul>
  		<h1 class="title">{{item.id}}</h1>
    	<li><h3><a href={{"%s/nuke"%item.id}}>Nuke comps</a></h3></li>
    </ul>
  %end
    </div>
 </body>
</html>