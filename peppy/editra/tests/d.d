#!/usr/bin/dmd -run
// Syntax Highlighting test file for D programming language
// A single line comment
/* A multi-line comment about this file.
 * Adopted from http://en.wikipedia.org/wiki/D_%28programming_language%29
 */
 
import std.stdio;
int main(char[][] args)                 
{
    writefln("Hello World");
 
    // Strings are denoted as a dynamic array of chars 'char[]'
    // auto type inference and built-in foreach
    foreach(argc, argv; args)
    {
        auto cl = new CmdLin(argc, argv);    // OOP is supported
        writefln(cl.argnum, cl.suffix, " arg: %s", cl.argv);  // user-defined class properties.
 
        delete cl;   // Garbage Collection or explicit memory management - your choice
    }
 
    // Nested structs, classes and functions
    struct specs
    {
        // all vars automatically initialized to 0 at runtime
        int count, allocated;
        // however you can choose to avoid array initialization
        int[10000] bigarray = void;
    }
 
    specs argspecs(char[][] args)
    // Optional (built-in) function contracts.
    in
    {
        assert(args.length > 0);                   // assert built in
    }
    out(result)
    {
        assert(result.count == CmdLin.total);
        assert(result.allocated > 0);
    }
    body
    {
        specs* s = new specs;
        // no need for '->'
        s.count = args.length;  // The 'length' property is number of elements.
        s.allocated = typeof(args).sizeof; // built-in properties for native types
        foreach(arg; args)
            s.allocated += arg.length * typeof(arg[0]).sizeof;
        return *s;
    }
 
    // built-in string and common string operations, eg. '~' is concatenate.
    char[] argcmsg  = "argc = %d";
    char[] allocmsg = "allocated = %d";
    writefln(argcmsg ~ ", " ~ allocmsg,
            argspecs(args).count,argspecs(args).allocated);
    return 0;
}
 
/**
 * Stores a single command line argument.
 */
class CmdLin
{
    private
    {
        int _argc;
        char[] _argv;
        static uint _totalc;
    }
 
    public:
        /**
         * Object constructor.
         * params:
         *   argc = ordinal count of this argument.
         *   argv = text of the parameter
         */
        this(int argc, char[] argv)
        {
            _argc = argc + 1;
            _argv = argv;
            _totalc++;
        }
 
        ~this() // Object destructor
        {
            // Doesn't actually do anything for this example.
        }
 
        int argnum() // A property that returns arg number
        {
            return _argc;
        }
 
        char[] argv() // A property that returns arg text
        {
            return _argv;
        }
 
        wchar[] suffix() // A property that returns ordinal suffix
        {
            wchar[] suffix; // Built in Unicode strings (UTF-8, UTF-16, UTF-32)
            switch(_argc)
            {
                case 1:
                    suffix = "st";
                    break;
                case 2:
                    suffix = "nd";
                    break;
                case 3:
                    suffix = "rd";
                    break;
                default:  // 'default' is mandatory with "-w" compile switch.
                    suffix = "th";
            }
            return suffix;
        }
 
        /**
          * A static property, as in C++ or Java,
          * applying to the class object rather than instances.
          * returns: The total number of commandline args added.
          */
        static typeof(_totalc) total()
        {
            return _totalc;
        }
 
        // Class invariant, things that must be true after any method is run.
        invariant ()
        {
            assert(_argc > 0);
            assert(_totalc >= _argc);
        }
}