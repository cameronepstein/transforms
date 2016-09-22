#!/usr/bin/perl
use strict;
use CGI;

#my $Python = "/Library/Frameworks/Python.framework/Versions/Current/bin/python";
my $Python = "python"; # if you have problems, try the above
my $pythonprog="transform_app.py";
my $CGIquery=new CGI;
print "Content-type: text/xml\n\n";

my $postdata = $CGIquery->param('POSTDATA');
my $query_string = $ENV{'QUERY_STRING'};

##named pipes
open PYTHON,"| $Python $pythonprog \"$query_string\"" || die "Cant fork!";
local $SIG{PIPE} = sub { die "Pipe burst" };
print PYTHON $postdata;
while (<PYTHON>){
  print $_;
}
close (PYTHON);
