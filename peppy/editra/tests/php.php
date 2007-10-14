<?php
    /* Some comments about this file */
    // Comment line
    $hello = "HELLO"
    $world = "WORLD"

    function print_mood()
    {
        switch($_GET['friendly'])
        {
            case "yes":
                echo "<h1>$hello $world</h1>";
                break;
            case "no":
                echo "<h1>Bah!!</h1>"
                break;
            default:
                echo "<h1>$hello???</h1>";
        } 
    }
    function disp_date ()
    {
	    $tics=time();
	    echo date("m/d/Y",$tics);
    }

    include_once($hello_root_path . 'hellolib.php');
?>

<html>
   <head>
      <!-- Some Embedded HTML -->
      <title>Hello.php</title>
   </head>
   <body>
      <div>
        <p>Today is <?php disp_date() ?> and this website says <?php print_mood() ?></p>
      </div>
   </body>
</html>

