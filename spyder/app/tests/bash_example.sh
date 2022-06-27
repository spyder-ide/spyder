set -exou

TEMP_DIR=$1

echo "This is a temporary file created by $(uname)" > $TEMP_DIR/output_file.txt
