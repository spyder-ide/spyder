# Get text for last commit
LAST_COMMIT_TEXT="$(git log -1 --pretty=format:%s)"
echo "Last commit text: $LAST_COMMIT_TEXT"

# Use a regex and grep to count found patterns
COUNT=$(echo "$LAST_COMMIT_TEXT" | grep -c -E "\[ci skip\]|\[skip ci\]")
echo "Results: $COUNT"

if [[ $COUNT == '0' ]]; then 
  echo "Run build!"
  echo "::set-env name=RUN_BUILD::true"
else
  echo "Skip build! Commits including the filter: $COUNT"
  echo "::set-env name=RUN_BUILD::false"
fi

echo " "
