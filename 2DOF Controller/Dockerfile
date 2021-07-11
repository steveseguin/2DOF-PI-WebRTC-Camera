

RUN python3 -m pip install jsonschema Adafruit_GPIO

ADD app /app
WORKDIR /app

ENV PYTHONUNBUFFERED=1
CMD ["python3","server.py"]

# Build time is about 90 min
# docker buildx build --platform linux/arm/v7 --pull --rm -f "Dockerfile" -t obs-cam:controller "."
# docker build  --pull --rm -f "Dockerfile" -t obs-cam:controller "."
# docker run -d --network host --privileged --env-file env_file --name obs-cam obs-cam:controller
