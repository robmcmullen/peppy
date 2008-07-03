// Syntax Highlighting Test File for Vala
// Comments are like this
/* Multiline comments are like
 * this.
 */

// Hello World in Vala
using GLib;

//! \summary Documentation keyword
public class Sample : Object {
        public Sample () {
        }

        public void run () {
                stdout.printf ("Hello World\n");
                stdout.printf ("Unclosed string);
                stdout.printf ('a'); // <- Char
        }

        static int main (string[] args) {
                var sample = new Sample ();
                sample.run ();
                return 0;
        }
}
