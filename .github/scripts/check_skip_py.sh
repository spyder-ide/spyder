# Check if files ending in .py changed on the current PR
BASE_REF=$(git rev-parse origin/$GITHUB_BASE_REF)
HEAD_REF=$(git rev-parse HEAD)
echo "base: $BASE_REF"
echo "head: $HEAD_REF"
FILES=$(git diff --name-only $BASE_REF $HEAD_REF)
COUNT=$(echo $FILES | grep -c ".*\.py.*")

echo "Files including the filter: $FILES"
echo "Py files filter count: $COUNT"

if [[ $COUNT == '0' ]]; then 
  echo "Skip Py!"
  echo "::set-env name=RUN_BUILD_PY::false"
else
  echo "Run Py!"
  echo "::set-env name=RUN_BUILD_PY::true"
fi

echo " "
