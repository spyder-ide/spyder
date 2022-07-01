# Get text for last commit
LAST_COMMIT_TEXT="$(git log -1 --pretty=format:%s)"
echo "Last commit text: $LAST_COMMIT_TEXT"

# Use a regex and grep to count found patterns
COUNT=$(echo "$LAST_COMMIT_TEXT" | grep -c -E "\[ci skip\]|\[skip ci\]")
echo "Results: $COUNT"

if [[ $COUNT == '0' ]]; then
  echo "Run build!"
  echo "RUN_BUILD=true" >> $GITHUB_ENV
else
  echo "Skip build! Commits including the filter: $COUNT"
  echo "RUN_BUILD=false" >> $GITHUB_ENV
fi

echo " "
