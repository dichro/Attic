#!/usr/bin/perl -wl

use strict;

use Image::ExifTool;
use Data::Dumper;
use Digest::MD5 qw(md5_hex);

my $et = new Image::ExifTool;
$et->Options(FastScan => 2);

my %digests;

my %skipped;

while(<>) {
  chomp;
  my $thumb = $et->ImageInfo($_, ['Model', 'thumbnailimage']);
  #my $thumb = $et->ImageInfo($_);
  if(exists $thumb->{'Error'}) {
    warn $_, $thumb->{'Error'};
    next;
  }
  my $model = $et->{Model} || "no model";
  if($model ne "NEX-5") {
    $skipped{$model}++;
    next;
  }
  unless(exists $thumb->{'ThumbnailImage'}) {
    $skipped{"no thumb"}++;
    next;
  }
  my $digest = md5_hex(${$thumb->{'ThumbnailImage'}});
  $thumb->{"path"} = $_;
  s|.*/||;
  $thumb->{"file"} = $_;
  $digests{$digest} ||= [];
  push @{$digests{$digest}}, $thumb;
}

my %results;

foreach my $digest (keys %digests) {
  my @files = @{$digests{$digest}};
  if(scalar(@files) == 1) {
    # sometimes there's just one copy
    $results{"single"}++;
    next;
  }
  my %filenames;
  @filenames{map { $_->{"file"} } @files} = ();
  my @filenames = keys %filenames;
  if(scalar(@filenames) == 1) {
    # sometimes the same hash+filename lives in multiple directories
    $results{"multiple copies"}++;
    next;
  }
  if(scalar(grep { $_ =~ /^DSC/ } @filenames) == 1) {
    # sometimes it's one file from the card and the rest from fe-fi
    $results{"single eye-fi plus fe-fi"}++;
    next;
  }
  $results{"unhandled"}++;
}

foreach my $model (keys %results) {
  print "Results $results{$model} from $model";
}

foreach my $model (keys %skipped) {
  print "Skipped $skipped{$model} from $model";
}

#print Dumper(\%images);
