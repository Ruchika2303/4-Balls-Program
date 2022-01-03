import processing.core.PApplet;

import java.util.ArrayList;

public class OOPFourBall extends PApplet {

    public static final int HEIGHT = 480;
    public static final int WIDTH = 640;
    public static ArrayList<Ball> balls = new ArrayList<>();

    @Override
    public void settings() {
        size(WIDTH, HEIGHT);
    }

    @Override
    public void setup() {
        for (int speed = 1; speed <= 4; speed++) {
            balls.add(new Ball(speed, speed * HEIGHT / 5));
        }
    }

    @Override
    public void draw() {
        for (Ball ball : balls) {
            ball.ball(this);
            ball.newPosition();
        }
    }

    public static void main(String[] args) {
        PApplet.main("OOPFourBall",args);
    }
}
