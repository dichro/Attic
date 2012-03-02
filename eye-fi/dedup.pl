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
  my $size = (stat $_)[7];
  unless($size > 10000) {
    # too short to be believable
    $skipped{"too short"}++;
    next;
  }
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
  # digesting thumbnail to make a unique id. This works way
  # better than I expected. I'm also assuming that the thumbnail
  # is a header (rather than a footer) so it's likely to be
  # present for truncated images too.
  my $digest = md5_hex(${$thumb->{'ThumbnailImage'}});
  $thumb->{"path"} = $_;
  s|.*/||;
  @{$thumb}{"file", "size"} = ($_, $size);
  delete @{$thumb}{'Model', 'ThumbnailImage'};
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
  my $result = choose(@filenames);
  print "$result ", Dumper(\@files) unless $results{$result}++ > 2;
}

sub choose {
  my @filenames = @_;
  # sometimes the same hash+filename lives in multiple directories
  return "multiple copies" if scalar(@filenames) == 1;
  my $dscs = scalar(grep { $_ =~ /^DSC/ } @filenames);
  # sometimes it's one file from the card and the rest from fe-fi
  return "single eye-fi plus fe-fi" if $dscs == 1;
  # sometimes there's no matching file from the card
  return "no eye-fi" if $dscs == 0;
  # or... we have no idea
  return "unhandled";
}

foreach my $model (keys %results) {
  print "Results $results{$model} from $model";
}

foreach my $model (keys %skipped) {
  print "Skipped $skipped{$model} from $model";
}

#print Dumper(\%images);
